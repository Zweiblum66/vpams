"""
Core detection engine for intrusion detection system.

Coordinates network monitoring, anomaly detection, signature matching,
and threat intelligence correlation.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog
from enum import Enum

from .config import get_settings
from .exceptions import DetectionEngineError, AnomalyDetectionError
from ..models.schemas import (
    SecurityEvent, ThreatLevel, EventType, NetworkPacket,
    AnomalyResult, ThreatIntelMatch
)
from ..services.network_monitor import NetworkMonitor
from ..services.anomaly_detector import AnomalyDetector
from ..services.signature_matcher import SignatureMatcher
from ..services.threat_intelligence import ThreatIntelligence
from ..services.host_monitor import HostMonitor


logger = structlog.get_logger()


class DetectionMode(Enum):
    """Detection engine operation modes."""
    ACTIVE = "active"      # Full detection and alerting
    PASSIVE = "passive"    # Detection only, no automated response
    LEARNING = "learning"  # Learning mode for anomaly detection


@dataclass
class DetectionResult:
    """Result of intrusion detection analysis."""
    event_id: str
    timestamp: datetime
    threat_level: ThreatLevel
    event_type: EventType
    source_ip: Optional[str] = None
    target_ip: Optional[str] = None
    description: str = ""
    confidence: float = 0.0
    signatures_matched: List[str] = None
    anomaly_score: float = 0.0
    threat_intel_matches: List[ThreatIntelMatch] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.signatures_matched is None:
            self.signatures_matched = []
        if self.threat_intel_matches is None:
            self.threat_intel_matches = []
        if self.metadata is None:
            self.metadata = {}


class DetectionEngine:
    """Main detection engine coordinating all detection components."""
    
    def __init__(self):
        self.settings = get_settings()
        self.mode = DetectionMode(self.settings.ids_mode)
        
        # Detection components
        self.network_monitor: Optional[NetworkMonitor] = None
        self.anomaly_detector: Optional[AnomalyDetector] = None
        self.signature_matcher: Optional[SignatureMatcher] = None
        self.threat_intelligence: Optional[ThreatIntelligence] = None
        self.host_monitor: Optional[HostMonitor] = None
        
        # State tracking
        self.active_events: Dict[str, SecurityEvent] = {}
        self.event_correlation: Dict[str, List[str]] = {}
        self.detection_stats = {
            "events_processed": 0,
            "threats_detected": 0,
            "false_positives": 0,
            "last_update": datetime.utcnow()
        }
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize detection engine and all components."""
        try:
            logger.info("Initializing detection engine")
            
            # Initialize network monitoring
            if self.settings.ids_enabled:
                self.network_monitor = NetworkMonitor()
                await self.network_monitor.initialize()
                logger.info("Network monitor initialized")
            
            # Initialize anomaly detection
            if self.settings.anomaly_detection_enabled:
                self.anomaly_detector = AnomalyDetector()
                await self.anomaly_detector.initialize()
                logger.info("Anomaly detector initialized")
            
            # Initialize signature matcher
            self.signature_matcher = SignatureMatcher()
            await self.signature_matcher.initialize()
            logger.info("Signature matcher initialized")
            
            # Initialize threat intelligence
            if self.settings.threat_intel_enabled:
                self.threat_intelligence = ThreatIntelligence()
                await self.threat_intelligence.initialize()
                logger.info("Threat intelligence initialized")
            
            # Initialize host monitoring
            if self.settings.host_monitoring_enabled:
                self.host_monitor = HostMonitor()
                await self.host_monitor.initialize()
                logger.info("Host monitor initialized")
            
            # Start background tasks
            await self._start_background_tasks()
            self._running = True
            
            logger.info(
                "Detection engine initialized",
                mode=self.mode.value,
                components_active={
                    "network_monitor": self.network_monitor is not None,
                    "anomaly_detector": self.anomaly_detector is not None,
                    "signature_matcher": self.signature_matcher is not None,
                    "threat_intelligence": self.threat_intelligence is not None,
                    "host_monitor": self.host_monitor is not None
                }
            )
            
        except Exception as e:
            logger.error("Failed to initialize detection engine", error=str(e))
            raise DetectionEngineError(f"Initialization failed: {str(e)}")
    
    async def _start_background_tasks(self) -> None:
        """Start background monitoring and processing tasks."""
        if self.network_monitor:
            task = asyncio.create_task(self._network_monitoring_loop())
            self._tasks.append(task)
        
        if self.host_monitor:
            task = asyncio.create_task(self._host_monitoring_loop())
            self._tasks.append(task)
        
        # Statistics update task
        task = asyncio.create_task(self._stats_update_loop())
        self._tasks.append(task)
        
        # Event correlation task
        task = asyncio.create_task(self._event_correlation_loop())
        self._tasks.append(task)
        
        logger.info(f"Started {len(self._tasks)} background tasks")
    
    async def _network_monitoring_loop(self) -> None:
        """Background network monitoring loop."""
        while self._running:
            try:
                # Get network packets from monitor
                packets = await self.network_monitor.get_packets(batch_size=100)
                
                for packet in packets:
                    await self._process_network_packet(packet)
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error("Error in network monitoring loop", error=str(e))
                await asyncio.sleep(1)
    
    async def _host_monitoring_loop(self) -> None:
        """Background host monitoring loop."""
        while self._running:
            try:
                # Get host events from monitor
                events = await self.host_monitor.get_events(batch_size=50)
                
                for event in events:
                    await self._process_host_event(event)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("Error in host monitoring loop", error=str(e))
                await asyncio.sleep(1)
    
    async def _stats_update_loop(self) -> None:
        """Background statistics update loop."""
        while self._running:
            try:
                await self._update_statistics()
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error("Error in stats update loop", error=str(e))
                await asyncio.sleep(60)
    
    async def _event_correlation_loop(self) -> None:
        """Background event correlation loop."""
        while self._running:
            try:
                await self._correlate_events()
                await asyncio.sleep(10)  # Correlate every 10 seconds
                
            except Exception as e:
                logger.error("Error in event correlation loop", error=str(e))
                await asyncio.sleep(10)
    
    async def _process_network_packet(self, packet: NetworkPacket) -> None:
        """Process a single network packet for threats."""
        try:
            results: List[DetectionResult] = []
            
            # Signature detection
            if self.signature_matcher:
                signature_matches = await self.signature_matcher.match_packet(packet)
                if signature_matches:
                    for match in signature_matches:
                        result = DetectionResult(
                            event_id=f"sig_{int(time.time() * 1000000)}",
                            timestamp=datetime.utcnow(),
                            threat_level=ThreatLevel(match.severity),
                            event_type=EventType.SIGNATURE_MATCH,
                            source_ip=packet.source_ip,
                            target_ip=packet.dest_ip,
                            description=match.description,
                            confidence=match.confidence,
                            signatures_matched=[match.signature_id],
                            metadata={"packet_id": packet.id}
                        )
                        results.append(result)
            
            # Anomaly detection
            if self.anomaly_detector and self.mode != DetectionMode.LEARNING:
                anomaly_result = await self.anomaly_detector.analyze_packet(packet)
                if anomaly_result.is_anomaly:
                    result = DetectionResult(
                        event_id=f"anom_{int(time.time() * 1000000)}",
                        timestamp=datetime.utcnow(),
                        threat_level=self._anomaly_score_to_threat_level(anomaly_result.score),
                        event_type=EventType.ANOMALY,
                        source_ip=packet.source_ip,
                        target_ip=packet.dest_ip,
                        description=f"Network anomaly detected: {anomaly_result.anomaly_type}",
                        confidence=anomaly_result.confidence,
                        anomaly_score=anomaly_result.score,
                        metadata={
                            "anomaly_type": anomaly_result.anomaly_type,
                            "packet_id": packet.id
                        }
                    )
                    results.append(result)
            
            # Threat intelligence correlation
            if self.threat_intelligence:
                threat_matches = await self.threat_intelligence.check_ip(packet.source_ip)
                if threat_matches:
                    for match in threat_matches:
                        result = DetectionResult(
                            event_id=f"intel_{int(time.time() * 1000000)}",
                            timestamp=datetime.utcnow(),
                            threat_level=ThreatLevel(match.threat_level),
                            event_type=EventType.THREAT_INTELLIGENCE,
                            source_ip=packet.source_ip,
                            target_ip=packet.dest_ip,
                            description=f"Threat intelligence match: {match.description}",
                            confidence=match.confidence,
                            threat_intel_matches=[match],
                            metadata={"packet_id": packet.id}
                        )
                        results.append(result)
            
            # Process detection results
            for result in results:
                await self._handle_detection_result(result)
            
            self.detection_stats["events_processed"] += 1
            
        except Exception as e:
            logger.error("Error processing network packet", packet_id=packet.id, error=str(e))
    
    async def _process_host_event(self, event: Dict[str, Any]) -> None:
        """Process a host-based security event."""
        try:
            # Create detection result from host event
            result = DetectionResult(
                event_id=f"host_{int(time.time() * 1000000)}",
                timestamp=datetime.utcnow(),
                threat_level=ThreatLevel(event.get("threat_level", "low")),
                event_type=EventType.HOST_BASED,
                description=event.get("description", "Host-based security event"),
                confidence=event.get("confidence", 0.8),
                metadata=event
            )
            
            await self._handle_detection_result(result)
            
        except Exception as e:
            logger.error("Error processing host event", event=event, error=str(e))
    
    async def _handle_detection_result(self, result: DetectionResult) -> None:
        """Handle a detection result based on current mode and threat level."""
        try:
            # Log the detection
            logger.info(
                "Security event detected",
                event_id=result.event_id,
                threat_level=result.threat_level.value,
                event_type=result.event_type.value,
                source_ip=result.source_ip,
                description=result.description,
                confidence=result.confidence
            )
            
            # Update statistics
            if result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                self.detection_stats["threats_detected"] += 1
            
            # Store active event
            security_event = SecurityEvent(
                id=result.event_id,
                timestamp=result.timestamp,
                event_type=result.event_type,
                threat_level=result.threat_level,
                source_ip=result.source_ip,
                target_ip=result.target_ip,
                description=result.description,
                confidence=result.confidence,
                metadata=result.metadata,
                status="active"
            )
            
            self.active_events[result.event_id] = security_event
            
            # Take action based on mode and threat level
            if self.mode == DetectionMode.ACTIVE:
                await self._take_automated_action(result)
            
        except Exception as e:
            logger.error("Error handling detection result", event_id=result.event_id, error=str(e))
    
    async def _take_automated_action(self, result: DetectionResult) -> None:
        """Take automated response action based on detection result."""
        try:
            # High and critical threats trigger immediate response
            if result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                
                # Block source IP if available
                if result.source_ip and self.network_monitor:
                    await self.network_monitor.block_ip(result.source_ip, duration=3600)
                    logger.info("Blocked malicious IP", ip=result.source_ip, event_id=result.event_id)
                
                # Send immediate alert
                await self._send_alert(result)
            
            elif result.threat_level == ThreatLevel.MEDIUM:
                # Medium threats get throttled response
                await self._send_alert(result)
            
        except Exception as e:
            logger.error("Error taking automated action", event_id=result.event_id, error=str(e))
    
    async def _send_alert(self, result: DetectionResult) -> None:
        """Send alert for security event."""
        # Implementation would send alerts via webhook, email, etc.
        logger.info("Alert sent", event_id=result.event_id, threat_level=result.threat_level.value)
    
    def _anomaly_score_to_threat_level(self, score: float) -> ThreatLevel:
        """Convert anomaly score to threat level."""
        if score >= 0.9:
            return ThreatLevel.CRITICAL
        elif score >= 0.7:
            return ThreatLevel.HIGH
        elif score >= 0.5:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
    
    async def _correlate_events(self) -> None:
        """Correlate related security events."""
        try:
            # Group events by source IP and time window
            time_window = timedelta(minutes=5)
            current_time = datetime.utcnow()
            
            ip_events: Dict[str, List[SecurityEvent]] = {}
            
            for event in self.active_events.values():
                if event.source_ip and (current_time - event.timestamp) <= time_window:
                    if event.source_ip not in ip_events:
                        ip_events[event.source_ip] = []
                    ip_events[event.source_ip].append(event)
            
            # Look for correlated attack patterns
            for source_ip, events in ip_events.items():
                if len(events) >= 3:  # Multiple events from same IP
                    await self._create_correlated_event(source_ip, events)
            
        except Exception as e:
            logger.error("Error correlating events", error=str(e))
    
    async def _create_correlated_event(self, source_ip: str, events: List[SecurityEvent]) -> None:
        """Create a correlated security event."""
        try:
            # Calculate overall threat level
            max_threat = max(event.threat_level for event in events)
            
            correlated_event = SecurityEvent(
                id=f"corr_{int(time.time() * 1000000)}",
                timestamp=datetime.utcnow(),
                event_type=EventType.CORRELATED_ATTACK,
                threat_level=max_threat,
                source_ip=source_ip,
                description=f"Correlated attack pattern from {source_ip} ({len(events)} events)",
                confidence=min(1.0, sum(event.confidence for event in events) / len(events)),
                metadata={
                    "related_events": [event.id for event in events],
                    "event_count": len(events),
                    "time_span": (max(event.timestamp for event in events) - 
                                min(event.timestamp for event in events)).total_seconds()
                },
                status="active"
            )
            
            self.active_events[correlated_event.id] = correlated_event
            
            logger.info(
                "Correlated attack detected",
                source_ip=source_ip,
                event_count=len(events),
                threat_level=max_threat.value
            )
            
        except Exception as e:
            logger.error("Error creating correlated event", source_ip=source_ip, error=str(e))
    
    async def _update_statistics(self) -> None:
        """Update detection engine statistics."""
        try:
            self.detection_stats["last_update"] = datetime.utcnow()
            
            # Clean up old events
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            expired_events = [
                event_id for event_id, event in self.active_events.items()
                if event.timestamp < cutoff_time
            ]
            
            for event_id in expired_events:
                del self.active_events[event_id]
            
            logger.debug(
                "Statistics updated",
                active_events=len(self.active_events),
                events_processed=self.detection_stats["events_processed"],
                threats_detected=self.detection_stats["threats_detected"]
            )
            
        except Exception as e:
            logger.error("Error updating statistics", error=str(e))
    
    async def get_active_events(self) -> List[SecurityEvent]:
        """Get list of currently active security events."""
        return list(self.active_events.values())
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get detection engine statistics."""
        return {
            **self.detection_stats,
            "active_events": len(self.active_events),
            "mode": self.mode.value,
            "components_status": {
                "network_monitor": self.network_monitor is not None and self.network_monitor.is_running(),
                "anomaly_detector": self.anomaly_detector is not None,
                "signature_matcher": self.signature_matcher is not None,
                "threat_intelligence": self.threat_intelligence is not None,
                "host_monitor": self.host_monitor is not None and self.host_monitor.is_running()
            }
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources and stop background tasks."""
        try:
            self._running = False
            
            # Cancel background tasks
            for task in self._tasks:
                task.cancel()
            
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Cleanup components
            if self.network_monitor:
                await self.network_monitor.cleanup()
            
            if self.host_monitor:
                await self.host_monitor.cleanup()
            
            if self.threat_intelligence:
                await self.threat_intelligence.cleanup()
            
            logger.info("Detection engine cleanup completed")
            
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))