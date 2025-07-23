"""
Remote Production Service for distributed live production workflows
"""

import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import aiofiles
from pathlib import Path
import uuid
import tempfile
import websockets
import aiohttp

from ..core.logging import get_logger
from ..core.exceptions import ProxyGenerationError

logger = get_logger(__name__)


class RemoteProductionRole(Enum):
    """Production roles for remote team members"""
    DIRECTOR = "director"
    PRODUCER = "producer"
    CAMERA_OP = "camera_operator"
    AUDIO_OP = "audio_operator"
    GRAPHICS_OP = "graphics_operator"
    SWITCHER = "switcher"
    ENGINEER = "engineer"
    TALENT = "talent"
    OBSERVER = "observer"


class CommunicationChannel(Enum):
    """Communication channels for production teams"""
    PROGRAM = "program"  # Main program audio
    DIRECTOR = "director"  # Director's channel
    TECHNICAL = "technical"  # Technical crew
    TALENT = "talent"  # Talent IFB
    PRIVATE = "private"  # Private conversations
    EMERGENCY = "emergency"  # Emergency communications


class RemoteSourceType(Enum):
    """Types of remote production sources"""
    CAMERA = "camera"
    SCREEN_SHARE = "screen_share"
    MOBILE = "mobile"
    SATELLITE = "satellite"
    BONDED_CELLULAR = "bonded_cellular"
    SRT = "srt"
    RTMP = "rtmp"
    NDI = "ndi"
    WEBRTC = "webrtc"


class TallyState(Enum):
    """Tally light states for remote cameras"""
    OFF = "off"
    PREVIEW = "preview"  # Green
    PROGRAM = "program"  # Red
    NEXT = "next"  # Yellow/Amber


class ReturnFeedType(Enum):
    """Types of return feeds for remote participants"""
    PROGRAM_CLEAN = "program_clean"
    PROGRAM_DIRTY = "program_dirty"  # With graphics
    MULTIVIEW = "multiview"
    PREVIEW = "preview"
    CUSTOM = "custom"
    CONFIDENCE = "confidence"  # Their own feed


class RemoteProductionService:
    """Service for managing remote production workflows"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.obs_websocket_url = "ws://localhost:4444"  # OBS WebSocket
        self.vmix_api_url = "http://localhost:8088"  # vMix API
        
        # Active remote productions
        self.active_productions = {}
        
        # WebRTC signaling server
        self.signaling_server = None
        
        # Communication channels
        self.comm_channels = {}
        
        # Source registry
        self.remote_sources = {}
        
        # Return feed configurations
        self.return_feeds = {}
        
        # Tally system
        self.tally_states = {}
    
    async def create_remote_production(
        self,
        production_id: str,
        production_name: str,
        director_id: str,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new remote production session
        
        Args:
            production_id: Unique production identifier
            production_name: Human-readable production name
            director_id: User ID of the director
            configuration: Production configuration
        
        Returns:
            Production session information
        """
        try:
            # Create production session
            production = {
                "id": production_id,
                "name": production_name,
                "director_id": director_id,
                "created_at": datetime.utcnow(),
                "status": "preparing",
                "configuration": configuration,
                "participants": {},
                "sources": {},
                "comm_channels": {},
                "recordings": {},
                "metrics": {
                    "start_time": None,
                    "duration": 0,
                    "total_participants": 0,
                    "total_sources": 0
                }
            }
            
            # Initialize communication channels
            for channel_type in CommunicationChannel:
                channel_id = f"{production_id}_{channel_type.value}"
                production["comm_channels"][channel_type.value] = {
                    "id": channel_id,
                    "type": channel_type.value,
                    "participants": [],
                    "muted": [],
                    "active": True
                }
            
            # Store production
            self.active_productions[production_id] = production
            
            # Start signaling server if needed
            if configuration.get("enable_webrtc", True):
                await self._start_signaling_server(production_id)
            
            logger.info(
                "remote_production_created",
                production_id=production_id,
                name=production_name
            )
            
            return {
                "production_id": production_id,
                "name": production_name,
                "status": "preparing",
                "join_url": f"/productions/{production_id}/join",
                "control_url": f"/productions/{production_id}/control",
                "created_at": production["created_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create remote production: {str(e)}")
            raise ProxyGenerationError(f"Remote production creation failed: {str(e)}")
    
    async def add_remote_participant(
        self,
        production_id: str,
        participant_id: str,
        participant_name: str,
        role: RemoteProductionRole,
        capabilities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a participant to remote production
        
        Args:
            production_id: Production session ID
            participant_id: Unique participant ID
            participant_name: Participant display name
            role: Production role
            capabilities: Participant capabilities (camera, audio, etc.)
        
        Returns:
            Participant configuration
        """
        if production_id not in self.active_productions:
            raise ProxyGenerationError(f"Production {production_id} not found")
        
        production = self.active_productions[production_id]
        
        # Create participant entry
        participant = {
            "id": participant_id,
            "name": participant_name,
            "role": role.value,
            "joined_at": datetime.utcnow(),
            "status": "connected",
            "capabilities": capabilities,
            "sources": [],
            "comm_channels": [],
            "permissions": self._get_role_permissions(role),
            "connection_quality": {
                "latency_ms": 0,
                "packet_loss": 0,
                "bandwidth_kbps": 0
            }
        }
        
        # Assign communication channels based on role
        participant["comm_channels"] = self._get_role_channels(role)
        
        # Add to production
        production["participants"][participant_id] = participant
        production["metrics"]["total_participants"] += 1
        
        # Add to appropriate comm channels
        for channel in participant["comm_channels"]:
            if channel in production["comm_channels"]:
                production["comm_channels"][channel]["participants"].append(participant_id)
        
        logger.info(
            "remote_participant_added",
            production_id=production_id,
            participant_id=participant_id,
            role=role.value
        )
        
        return {
            "participant_id": participant_id,
            "name": participant_name,
            "role": role.value,
            "permissions": participant["permissions"],
            "comm_channels": participant["comm_channels"],
            "rtc_config": await self._get_webrtc_config(production_id, participant_id)
        }
    
    async def add_remote_source(
        self,
        production_id: str,
        source_id: str,
        source_name: str,
        source_type: RemoteSourceType,
        participant_id: str,
        connection_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a remote video/audio source to production
        
        Args:
            production_id: Production session ID
            source_id: Unique source ID
            source_name: Source display name
            source_type: Type of remote source
            participant_id: Owner participant ID
            connection_params: Connection parameters for the source
        
        Returns:
            Source configuration
        """
        if production_id not in self.active_productions:
            raise ProxyGenerationError(f"Production {production_id} not found")
        
        production = self.active_productions[production_id]
        
        # Create source entry
        source = {
            "id": source_id,
            "name": source_name,
            "type": source_type.value,
            "participant_id": participant_id,
            "added_at": datetime.utcnow(),
            "status": "connecting",
            "connection_params": connection_params,
            "stream_url": None,
            "preview_url": None,
            "tally_state": TallyState.OFF.value,
            "metrics": {
                "resolution": None,
                "framerate": None,
                "bitrate": None,
                "codec": None,
                "latency_ms": 0
            }
        }
        
        # Start source connection based on type
        if source_type == RemoteSourceType.SRT:
            source["stream_url"] = await self._create_srt_receiver(source_id, connection_params)
        elif source_type == RemoteSourceType.RTMP:
            source["stream_url"] = await self._create_rtmp_receiver(source_id, connection_params)
        elif source_type == RemoteSourceType.WEBRTC:
            source["stream_url"] = await self._create_webrtc_receiver(source_id, connection_params)
        elif source_type == RemoteSourceType.NDI:
            source["stream_url"] = await self._create_ndi_receiver(source_id, connection_params)
        
        # Generate preview stream
        if source["stream_url"]:
            source["preview_url"] = await self._create_preview_stream(source_id, source["stream_url"])
        
        # Add to production
        production["sources"][source_id] = source
        production["metrics"]["total_sources"] += 1
        
        # Add to participant
        if participant_id in production["participants"]:
            production["participants"][participant_id]["sources"].append(source_id)
        
        # Store in registry
        self.remote_sources[source_id] = source
        
        logger.info(
            "remote_source_added",
            production_id=production_id,
            source_id=source_id,
            source_type=source_type.value
        )
        
        return {
            "source_id": source_id,
            "name": source_name,
            "type": source_type.value,
            "stream_url": source["stream_url"],
            "preview_url": source["preview_url"],
            "status": source["status"]
        }
    
    async def update_tally_state(
        self,
        production_id: str,
        source_id: str,
        tally_state: TallyState
    ) -> Dict[str, Any]:
        """
        Update tally light state for a remote source
        
        Args:
            production_id: Production session ID
            source_id: Source ID to update
            tally_state: New tally state
        
        Returns:
            Updated tally information
        """
        if production_id not in self.active_productions:
            raise ProxyGenerationError(f"Production {production_id} not found")
        
        production = self.active_productions[production_id]
        
        if source_id not in production["sources"]:
            raise ProxyGenerationError(f"Source {source_id} not found")
        
        # Update tally state
        old_state = production["sources"][source_id]["tally_state"]
        production["sources"][source_id]["tally_state"] = tally_state.value
        self.tally_states[source_id] = tally_state
        
        # Notify participant
        participant_id = production["sources"][source_id]["participant_id"]
        await self._send_tally_update(participant_id, source_id, tally_state)
        
        logger.info(
            "tally_state_updated",
            production_id=production_id,
            source_id=source_id,
            old_state=old_state,
            new_state=tally_state.value
        )
        
        return {
            "source_id": source_id,
            "tally_state": tally_state.value,
            "participant_id": participant_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def configure_return_feed(
        self,
        production_id: str,
        participant_id: str,
        feed_type: ReturnFeedType,
        custom_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Configure return video feed for a participant
        
        Args:
            production_id: Production session ID
            participant_id: Participant ID
            feed_type: Type of return feed
            custom_sources: List of source IDs for custom feed
        
        Returns:
            Return feed configuration
        """
        if production_id not in self.active_productions:
            raise ProxyGenerationError(f"Production {production_id} not found")
        
        production = self.active_productions[production_id]
        
        if participant_id not in production["participants"]:
            raise ProxyGenerationError(f"Participant {participant_id} not found")
        
        # Create return feed configuration
        feed_config = {
            "participant_id": participant_id,
            "feed_type": feed_type.value,
            "custom_sources": custom_sources or [],
            "stream_url": None,
            "latency_mode": "low",
            "include_audio": True,
            "resolution": "1280x720",
            "bitrate": "2000k"
        }
        
        # Generate return feed stream
        if feed_type == ReturnFeedType.PROGRAM_CLEAN:
            feed_config["stream_url"] = await self._create_program_feed(production_id, False)
        elif feed_type == ReturnFeedType.PROGRAM_DIRTY:
            feed_config["stream_url"] = await self._create_program_feed(production_id, True)
        elif feed_type == ReturnFeedType.MULTIVIEW:
            feed_config["stream_url"] = await self._create_multiview_feed(production_id)
        elif feed_type == ReturnFeedType.CUSTOM and custom_sources:
            feed_config["stream_url"] = await self._create_custom_feed(production_id, custom_sources)
        
        # Store configuration
        self.return_feeds[participant_id] = feed_config
        
        logger.info(
            "return_feed_configured",
            production_id=production_id,
            participant_id=participant_id,
            feed_type=feed_type.value
        )
        
        return feed_config
    
    async def send_comm_message(
        self,
        production_id: str,
        sender_id: str,
        channel: CommunicationChannel,
        message_type: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a message through communication channel
        
        Args:
            production_id: Production session ID
            sender_id: Sender participant ID
            channel: Communication channel
            message_type: Type of message (audio, text, signal)
            message_data: Message payload
        
        Returns:
            Message confirmation
        """
        if production_id not in self.active_productions:
            raise ProxyGenerationError(f"Production {production_id} not found")
        
        production = self.active_productions[production_id]
        channel_key = channel.value
        
        if channel_key not in production["comm_channels"]:
            raise ProxyGenerationError(f"Channel {channel_key} not found")
        
        # Check if sender has access to channel
        if sender_id not in production["comm_channels"][channel_key]["participants"]:
            raise ProxyGenerationError(f"Sender {sender_id} not authorized for channel {channel_key}")
        
        # Create message
        message = {
            "id": str(uuid.uuid4()),
            "sender_id": sender_id,
            "channel": channel_key,
            "type": message_type,
            "data": message_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Route message to channel participants
        recipients = []
        for participant_id in production["comm_channels"][channel_key]["participants"]:
            if participant_id != sender_id or message_data.get("include_sender", False):
                if participant_id not in production["comm_channels"][channel_key]["muted"]:
                    await self._route_comm_message(participant_id, message)
                    recipients.append(participant_id)
        
        logger.info(
            "comm_message_sent",
            production_id=production_id,
            sender_id=sender_id,
            channel=channel_key,
            recipients_count=len(recipients)
        )
        
        return {
            "message_id": message["id"],
            "channel": channel_key,
            "recipients": len(recipients),
            "timestamp": message["timestamp"]
        }
    
    async def create_iso_recording(
        self,
        production_id: str,
        source_id: str,
        output_path: str,
        include_timecode: bool = True
    ) -> Dict[str, Any]:
        """
        Create isolated recording of a remote source
        
        Args:
            production_id: Production session ID
            source_id: Source ID to record
            output_path: Path to save recording
            include_timecode: Whether to burn in timecode
        
        Returns:
            Recording information
        """
        if production_id not in self.active_productions:
            raise ProxyGenerationError(f"Production {production_id} not found")
        
        production = self.active_productions[production_id]
        
        if source_id not in production["sources"]:
            raise ProxyGenerationError(f"Source {source_id} not found")
        
        source = production["sources"][source_id]
        
        # Create recording configuration
        recording_id = str(uuid.uuid4())
        recording = {
            "id": recording_id,
            "source_id": source_id,
            "output_path": output_path,
            "start_time": datetime.utcnow(),
            "status": "recording",
            "include_timecode": include_timecode,
            "process": None
        }
        
        # Build FFmpeg command for ISO recording
        cmd = [
            self.ffmpeg_path,
            "-i", source["stream_url"],
            "-c:v", "copy",
            "-c:a", "copy"
        ]
        
        if include_timecode:
            # Add timecode overlay
            timecode = production["metrics"]["start_time"].strftime("%H:%M:%S:00")
            cmd.extend([
                "-vf", f"drawtext=text='{timecode}':timecode='{timecode}':rate=30:x=(w-tw)/2:y=h-th-10:fontsize=32:fontcolor=white:box=1:boxcolor=black@0.5"
            ])
        
        cmd.append(output_path)
        
        # Start recording process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        recording["process"] = process
        
        # Store recording
        if "recordings" not in production:
            production["recordings"] = {}
        production["recordings"][recording_id] = recording
        
        logger.info(
            "iso_recording_started",
            production_id=production_id,
            source_id=source_id,
            recording_id=recording_id
        )
        
        return {
            "recording_id": recording_id,
            "source_id": source_id,
            "status": "recording",
            "output_path": output_path,
            "start_time": recording["start_time"].isoformat()
        }
    
    async def get_production_metrics(self, production_id: str) -> Dict[str, Any]:
        """Get real-time metrics for a remote production"""
        if production_id not in self.active_productions:
            raise ProxyGenerationError(f"Production {production_id} not found")
        
        production = self.active_productions[production_id]
        
        # Calculate aggregate metrics
        total_bandwidth = 0
        avg_latency = 0
        connection_issues = []
        
        for source_id, source in production["sources"].items():
            if source["metrics"]["bitrate"]:
                total_bandwidth += source["metrics"]["bitrate"]
            if source["metrics"]["latency_ms"]:
                avg_latency += source["metrics"]["latency_ms"]
            
            # Check for issues
            if source["metrics"]["latency_ms"] > 500:
                connection_issues.append({
                    "source_id": source_id,
                    "issue": "high_latency",
                    "value": source["metrics"]["latency_ms"]
                })
        
        if production["sources"]:
            avg_latency = avg_latency / len(production["sources"])
        
        return {
            "production_id": production_id,
            "status": production["status"],
            "duration": (datetime.utcnow() - production["created_at"]).total_seconds(),
            "participants": {
                "total": len(production["participants"]),
                "by_role": self._count_by_role(production["participants"])
            },
            "sources": {
                "total": len(production["sources"]),
                "by_type": self._count_by_type(production["sources"]),
                "active": sum(1 for s in production["sources"].values() if s["status"] == "active")
            },
            "bandwidth": {
                "total_kbps": total_bandwidth,
                "avg_per_source": total_bandwidth / len(production["sources"]) if production["sources"] else 0
            },
            "latency": {
                "avg_ms": avg_latency,
                "min_ms": min((s["metrics"]["latency_ms"] for s in production["sources"].values()), default=0),
                "max_ms": max((s["metrics"]["latency_ms"] for s in production["sources"].values()), default=0)
            },
            "issues": connection_issues
        }
    
    async def _start_signaling_server(self, production_id: str):
        """Start WebRTC signaling server for production"""
        # Implementation would start a WebSocket server for WebRTC signaling
        pass
    
    async def _get_role_permissions(self, role: RemoteProductionRole) -> Dict[str, bool]:
        """Get permissions based on production role"""
        permissions = {
            "switch_sources": False,
            "adjust_audio": False,
            "control_graphics": False,
            "direct_talent": False,
            "technical_control": False,
            "view_multiview": False,
            "record_iso": False
        }
        
        if role == RemoteProductionRole.DIRECTOR:
            permissions.update({
                "switch_sources": True,
                "direct_talent": True,
                "view_multiview": True
            })
        elif role == RemoteProductionRole.SWITCHER:
            permissions.update({
                "switch_sources": True,
                "view_multiview": True
            })
        elif role == RemoteProductionRole.AUDIO_OP:
            permissions["adjust_audio"] = True
        elif role == RemoteProductionRole.GRAPHICS_OP:
            permissions["control_graphics"] = True
        elif role == RemoteProductionRole.ENGINEER:
            permissions.update({
                "technical_control": True,
                "view_multiview": True,
                "record_iso": True
            })
        
        return permissions
    
    async def _get_role_channels(self, role: RemoteProductionRole) -> List[str]:
        """Get communication channels for a role"""
        channels = []
        
        if role in [RemoteProductionRole.DIRECTOR, RemoteProductionRole.PRODUCER]:
            channels = [
                CommunicationChannel.DIRECTOR.value,
                CommunicationChannel.TECHNICAL.value,
                CommunicationChannel.EMERGENCY.value
            ]
        elif role in [RemoteProductionRole.SWITCHER, RemoteProductionRole.AUDIO_OP, 
                      RemoteProductionRole.GRAPHICS_OP, RemoteProductionRole.ENGINEER]:
            channels = [
                CommunicationChannel.TECHNICAL.value,
                CommunicationChannel.EMERGENCY.value
            ]
        elif role == RemoteProductionRole.TALENT:
            channels = [
                CommunicationChannel.TALENT.value,
                CommunicationChannel.EMERGENCY.value
            ]
        elif role == RemoteProductionRole.CAMERA_OP:
            channels = [
                CommunicationChannel.TECHNICAL.value,
                CommunicationChannel.EMERGENCY.value
            ]
        else:  # Observer
            channels = [CommunicationChannel.PROGRAM.value]
        
        return channels
    
    async def _get_webrtc_config(self, production_id: str, participant_id: str) -> Dict[str, Any]:
        """Get WebRTC configuration for participant"""
        return {
            "iceServers": [
                {"urls": ["stun:stun.l.google.com:19302"]},
                {"urls": ["stun:stun1.l.google.com:19302"]}
            ],
            "signaling_url": f"wss://signaling.mams.local/productions/{production_id}",
            "participant_token": self._generate_participant_token(participant_id)
        }
    
    async def _create_srt_receiver(self, source_id: str, params: Dict[str, Any]) -> str:
        """Create SRT receiver endpoint"""
        port = params.get("port", 9000)
        latency = params.get("latency", 120)
        
        # Return SRT listener URL
        return f"srt://0.0.0.0:{port}?mode=listener&latency={latency}"
    
    async def _create_rtmp_receiver(self, source_id: str, params: Dict[str, Any]) -> str:
        """Create RTMP receiver endpoint"""
        app_name = params.get("app", "live")
        stream_key = params.get("stream_key", source_id)
        
        # Return RTMP URL
        return f"rtmp://localhost:1935/{app_name}/{stream_key}"
    
    async def _create_webrtc_receiver(self, source_id: str, params: Dict[str, Any]) -> str:
        """Create WebRTC receiver endpoint"""
        # Return WebRTC stream URL (implementation specific)
        return f"webrtc://localhost:8443/sources/{source_id}"
    
    async def _create_ndi_receiver(self, source_id: str, params: Dict[str, Any]) -> str:
        """Create NDI receiver endpoint"""
        ndi_name = params.get("ndi_name", source_id)
        
        # Return NDI URL
        return f"ndi://{ndi_name}"
    
    async def _create_preview_stream(self, source_id: str, input_url: str) -> str:
        """Create low-resolution preview stream"""
        preview_url = f"http://localhost:8080/previews/{source_id}.m3u8"
        
        # FFmpeg command for preview generation would go here
        
        return preview_url
    
    async def _send_tally_update(self, participant_id: str, source_id: str, state: TallyState):
        """Send tally update to participant"""
        # Implementation would send tally state via WebSocket/WebRTC data channel
        pass
    
    async def _create_program_feed(self, production_id: str, include_graphics: bool) -> str:
        """Create program return feed"""
        feed_type = "dirty" if include_graphics else "clean"
        return f"http://localhost:8080/productions/{production_id}/program_{feed_type}.m3u8"
    
    async def _create_multiview_feed(self, production_id: str) -> str:
        """Create multiview return feed"""
        return f"http://localhost:8080/productions/{production_id}/multiview.m3u8"
    
    async def _create_custom_feed(self, production_id: str, source_ids: List[str]) -> str:
        """Create custom return feed from selected sources"""
        sources_str = "_".join(source_ids[:4])  # Limit to 4 sources
        return f"http://localhost:8080/productions/{production_id}/custom_{sources_str}.m3u8"
    
    async def _route_comm_message(self, participant_id: str, message: Dict[str, Any]):
        """Route communication message to participant"""
        # Implementation would send via WebSocket/WebRTC
        pass
    
    def _generate_participant_token(self, participant_id: str) -> str:
        """Generate secure token for participant"""
        # Implementation would generate JWT or similar
        return f"token_{participant_id}_{uuid.uuid4().hex[:8]}"
    
    def _count_by_role(self, participants: Dict[str, Any]) -> Dict[str, int]:
        """Count participants by role"""
        counts = {}
        for participant in participants.values():
            role = participant["role"]
            counts[role] = counts.get(role, 0) + 1
        return counts
    
    def _count_by_type(self, sources: Dict[str, Any]) -> Dict[str, int]:
        """Count sources by type"""
        counts = {}
        for source in sources.values():
            source_type = source["type"]
            counts[source_type] = counts.get(source_type, 0) + 1
        return counts
    
    def get_remote_production_capabilities(self) -> Dict[str, Any]:
        """Get remote production capabilities"""
        return {
            "roles": [r.value for r in RemoteProductionRole],
            "communication_channels": [c.value for c in CommunicationChannel],
            "source_types": [s.value for s in RemoteSourceType],
            "return_feed_types": [f.value for f in ReturnFeedType],
            "tally_states": [t.value for t in TallyState],
            "features": {
                "multi_source": True,
                "iso_recording": True,
                "return_feeds": True,
                "tally_lights": True,
                "intercom": True,
                "low_latency": True,
                "webrtc_support": True,
                "ndi_support": True,
                "bonded_cellular": True,
                "cloud_switching": True
            },
            "supported_protocols": [
                "SRT", "RTMP", "WebRTC", "NDI", "RTSP", "HLS"
            ],
            "max_participants": 50,
            "max_sources": 32,
            "max_return_feeds": 16
        }