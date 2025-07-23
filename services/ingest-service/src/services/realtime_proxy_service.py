"""
Real-time Proxy Generation Service for creating proxies during ingest
"""

import os
import asyncio
import subprocess
from typing import Dict, Optional, List, Tuple, Callable
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles
import structlog
from dataclasses import dataclass
from enum import Enum

from ..models.schemas import IngestJob, IngestStatus, ProxyType
from ..core.exceptions import ProxyGenerationError
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class ProxyQuality(Enum):
    """Proxy quality levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EDIT = "edit"


@dataclass
class ProxyProfile:
    """Profile for proxy generation"""
    name: str
    quality: ProxyQuality
    video_codec: str
    video_bitrate: str
    audio_codec: str
    audio_bitrate: str
    resolution: Optional[str] = None
    framerate: Optional[str] = None
    preset: str = "fast"


class RealtimeProxyService:
    """Service for generating proxies in real-time during ingest"""
    
    def __init__(self):
        self.active_generations: Dict[str, 'ProxyGenerationSession'] = {}
        self.proxy_profiles = self._initialize_profiles()
        
        # Configuration
        self.chunk_duration = 10  # seconds per chunk
        self.buffer_chunks = 3  # number of chunks to buffer
        self.max_parallel_chunks = 4
        self.output_format = "mp4"
        
    def _initialize_profiles(self) -> Dict[ProxyQuality, ProxyProfile]:
        """Initialize proxy generation profiles"""
        return {
            ProxyQuality.LOW: ProxyProfile(
                name="low_proxy",
                quality=ProxyQuality.LOW,
                video_codec="libx264",
                video_bitrate="500k",
                audio_codec="aac",
                audio_bitrate="64k",
                resolution="640x360",
                preset="ultrafast"
            ),
            ProxyQuality.MEDIUM: ProxyProfile(
                name="medium_proxy",
                quality=ProxyQuality.MEDIUM,
                video_codec="libx264",
                video_bitrate="1500k",
                audio_codec="aac",
                audio_bitrate="128k",
                resolution="1280x720",
                preset="fast"
            ),
            ProxyQuality.HIGH: ProxyProfile(
                name="high_proxy",
                quality=ProxyQuality.HIGH,
                video_codec="libx264",
                video_bitrate="3000k",
                audio_codec="aac",
                audio_bitrate="192k",
                resolution="1920x1080",
                preset="fast"
            ),
            ProxyQuality.EDIT: ProxyProfile(
                name="edit_proxy",
                quality=ProxyQuality.EDIT,
                video_codec="prores",
                video_bitrate="40000k",
                audio_codec="pcm_s16le",
                audio_bitrate="1536k",
                resolution=None,  # Keep original
                preset="fast"
            )
        }
    
    async def start_realtime_proxy(
        self,
        job_id: str,
        source_path: str,
        destination_dir: str,
        quality: ProxyQuality = ProxyQuality.MEDIUM,
        progress_callback: Optional[Callable] = None
    ) -> 'ProxyGenerationSession':
        """Start real-time proxy generation for an ingest job"""
        try:
            logger.info(
                "starting_realtime_proxy",
                job_id=job_id,
                source_path=source_path,
                quality=quality.value
            )
            
            # Create proxy generation session
            session = ProxyGenerationSession(
                job_id=job_id,
                source_path=source_path,
                destination_dir=destination_dir,
                profile=self.proxy_profiles[quality],
                service=self,
                progress_callback=progress_callback
            )
            
            self.active_generations[job_id] = session
            
            # Start proxy generation
            asyncio.create_task(session.start_generation())
            
            return session
            
        except Exception as e:
            logger.error(
                "realtime_proxy_start_failed",
                error=str(e),
                job_id=job_id
            )
            raise ProxyGenerationError(
                f"Failed to start real-time proxy: {str(e)}",
                error_code="PROXY_START_FAILED"
            )
    
    async def stop_realtime_proxy(self, job_id: str):
        """Stop real-time proxy generation"""
        try:
            if job_id in self.active_generations:
                session = self.active_generations[job_id]
                await session.stop_generation()
                del self.active_generations[job_id]
                
                logger.info("realtime_proxy_stopped", job_id=job_id)
                
        except Exception as e:
            logger.error(
                "realtime_proxy_stop_failed",
                error=str(e),
                job_id=job_id
            )
    
    async def get_proxy_status(self, job_id: str) -> Optional[Dict]:
        """Get status of real-time proxy generation"""
        if job_id not in self.active_generations:
            return None
        
        session = self.active_generations[job_id]
        return await session.get_status()
    
    async def generate_proxy_chunk(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        profile: ProxyProfile
    ) -> bool:
        """Generate a single proxy chunk"""
        try:
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-ss', str(start_time),
                '-t', str(duration),
                '-i', input_path,
                '-c:v', profile.video_codec,
                '-b:v', profile.video_bitrate,
                '-c:a', profile.audio_codec,
                '-b:a', profile.audio_bitrate,
                '-preset', profile.preset
            ]
            
            # Add resolution if specified
            if profile.resolution:
                cmd.extend(['-s', profile.resolution])
            
            # Add output options
            cmd.extend([
                '-movflags', '+faststart',
                '-y',
                output_path
            ])
            
            # Execute FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(
                    "proxy_chunk_generation_failed",
                    error=stderr.decode(),
                    start_time=start_time,
                    duration=duration
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(
                "proxy_chunk_error",
                error=str(e),
                input_path=input_path,
                output_path=output_path
            )
            return False
    
    async def concatenate_chunks(
        self,
        chunk_paths: List[str],
        output_path: str
    ) -> bool:
        """Concatenate proxy chunks into a single file"""
        try:
            # Create concat file
            concat_file = Path(output_path).parent / "concat_list.txt"
            
            async with aiofiles.open(concat_file, 'w') as f:
                for chunk_path in chunk_paths:
                    await f.write(f"file '{chunk_path}'\n")
            
            # FFmpeg concat command
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Clean up concat file
            concat_file.unlink()
            
            return process.returncode == 0
            
        except Exception as e:
            logger.error(
                "chunk_concatenation_failed",
                error=str(e),
                output_path=output_path
            )
            return False


class ProxyGenerationSession:
    """Represents an active proxy generation session"""
    
    def __init__(
        self,
        job_id: str,
        source_path: str,
        destination_dir: str,
        profile: ProxyProfile,
        service: RealtimeProxyService,
        progress_callback: Optional[Callable] = None
    ):
        self.job_id = job_id
        self.source_path = source_path
        self.destination_dir = destination_dir
        self.profile = profile
        self.service = service
        self.progress_callback = progress_callback
        
        # Session state
        self.is_active = False
        self.start_time = None
        self.chunks_generated = 0
        self.total_duration = 0
        self.current_position = 0
        self.chunk_paths: List[str] = []
        self.errors: List[str] = []
        
        # Output paths
        self.chunks_dir = Path(destination_dir) / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.proxy_path = Path(destination_dir) / f"{profile.name}.{service.output_format}"
        
        # Processing state
        self.chunk_queue: asyncio.Queue = asyncio.Queue()
        self.processing_tasks: List[asyncio.Task] = []
    
    async def start_generation(self):
        """Start the proxy generation process"""
        try:
            self.is_active = True
            self.start_time = datetime.utcnow()
            
            logger.info(
                "proxy_generation_started",
                job_id=self.job_id,
                profile=self.profile.name
            )
            
            # Start chunk processing tasks
            for i in range(self.service.max_parallel_chunks):
                task = asyncio.create_task(self._process_chunks())
                self.processing_tasks.append(task)
            
            # Start monitoring source file
            asyncio.create_task(self._monitor_source())
            
        except Exception as e:
            logger.error(
                "proxy_generation_start_error",
                error=str(e),
                job_id=self.job_id
            )
            self.is_active = False
            raise
    
    async def stop_generation(self):
        """Stop the proxy generation process"""
        try:
            self.is_active = False
            
            # Cancel processing tasks
            for task in self.processing_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
            
            # Concatenate all chunks if any were generated
            if self.chunk_paths:
                await self._finalize_proxy()
            
            logger.info(
                "proxy_generation_stopped",
                job_id=self.job_id,
                chunks_generated=self.chunks_generated
            )
            
        except Exception as e:
            logger.error(
                "proxy_generation_stop_error",
                error=str(e),
                job_id=self.job_id
            )
    
    async def get_status(self) -> Dict:
        """Get current status of proxy generation"""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'job_id': self.job_id,
            'profile': self.profile.name,
            'quality': self.profile.quality.value,
            'is_active': self.is_active,
            'chunks_generated': self.chunks_generated,
            'current_position': self.current_position,
            'total_duration': self.total_duration,
            'elapsed_time': elapsed,
            'proxy_path': str(self.proxy_path) if self.proxy_path.exists() else None,
            'errors': self.errors[-10:]  # Last 10 errors
        }
    
    async def _monitor_source(self):
        """Monitor source file and queue chunks for processing"""
        try:
            while self.is_active:
                # Get current file duration
                duration = await self._get_file_duration(self.source_path)
                
                if duration > self.current_position:
                    # Queue new chunks
                    while self.current_position < duration - self.service.chunk_duration:
                        chunk_info = {
                            'index': self.chunks_generated,
                            'start_time': self.current_position,
                            'duration': self.service.chunk_duration
                        }
                        
                        await self.chunk_queue.put(chunk_info)
                        self.current_position += self.service.chunk_duration
                        
                        logger.debug(
                            "chunk_queued",
                            job_id=self.job_id,
                            chunk_index=chunk_info['index'],
                            start_time=chunk_info['start_time']
                        )
                
                # Update total duration
                self.total_duration = duration
                
                # Wait before checking again
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(
                "source_monitoring_error",
                error=str(e),
                job_id=self.job_id
            )
            self.errors.append(f"Monitoring error: {str(e)}")
    
    async def _process_chunks(self):
        """Process chunks from the queue"""
        try:
            while self.is_active:
                try:
                    # Get chunk from queue with timeout
                    chunk_info = await asyncio.wait_for(
                        self.chunk_queue.get(),
                        timeout=10.0
                    )
                    
                    # Generate proxy chunk
                    chunk_path = self.chunks_dir / f"chunk_{chunk_info['index']:06d}.{self.service.output_format}"
                    
                    success = await self.service.generate_proxy_chunk(
                        input_path=self.source_path,
                        output_path=str(chunk_path),
                        start_time=chunk_info['start_time'],
                        duration=chunk_info['duration'],
                        profile=self.profile
                    )
                    
                    if success:
                        self.chunk_paths.append(str(chunk_path))
                        self.chunks_generated += 1
                        
                        # Update progress
                        if self.progress_callback:
                            await self.progress_callback({
                                'job_id': self.job_id,
                                'chunks_generated': self.chunks_generated,
                                'current_position': chunk_info['start_time'] + chunk_info['duration']
                            })
                        
                        logger.info(
                            "proxy_chunk_generated",
                            job_id=self.job_id,
                            chunk_index=chunk_info['index'],
                            chunk_path=str(chunk_path)
                        )
                        
                        # Periodically concatenate chunks
                        if self.chunks_generated % 10 == 0:
                            await self._update_proxy()
                    else:
                        self.errors.append(f"Failed to generate chunk {chunk_info['index']}")
                        
                except asyncio.TimeoutError:
                    # No chunks in queue, continue
                    continue
                    
        except asyncio.CancelledError:
            logger.info("chunk_processing_cancelled", job_id=self.job_id)
            raise
        except Exception as e:
            logger.error(
                "chunk_processing_error",
                error=str(e),
                job_id=self.job_id
            )
            self.errors.append(f"Processing error: {str(e)}")
    
    async def _update_proxy(self):
        """Update the proxy file with new chunks"""
        try:
            if len(self.chunk_paths) < 2:
                return
            
            # Create temporary proxy file
            temp_proxy = self.proxy_path.with_suffix('.tmp')
            
            success = await self.service.concatenate_chunks(
                chunk_paths=self.chunk_paths,
                output_path=str(temp_proxy)
            )
            
            if success:
                # Replace existing proxy
                if self.proxy_path.exists():
                    self.proxy_path.unlink()
                temp_proxy.rename(self.proxy_path)
                
                logger.info(
                    "proxy_updated",
                    job_id=self.job_id,
                    chunks_count=len(self.chunk_paths),
                    proxy_path=str(self.proxy_path)
                )
                
        except Exception as e:
            logger.error(
                "proxy_update_error",
                error=str(e),
                job_id=self.job_id
            )
            self.errors.append(f"Update error: {str(e)}")
    
    async def _finalize_proxy(self):
        """Finalize the proxy file"""
        try:
            # Final concatenation of all chunks
            await self._update_proxy()
            
            # Clean up chunk files
            for chunk_path in self.chunk_paths:
                try:
                    Path(chunk_path).unlink()
                except Exception:
                    pass
            
            logger.info(
                "proxy_finalized",
                job_id=self.job_id,
                proxy_path=str(self.proxy_path),
                total_chunks=self.chunks_generated
            )
            
        except Exception as e:
            logger.error(
                "proxy_finalization_error",
                error=str(e),
                job_id=self.job_id
            )
            self.errors.append(f"Finalization error: {str(e)}")
    
    async def _get_file_duration(self, file_path: str) -> float:
        """Get duration of media file using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and stdout:
                return float(stdout.decode().strip())
            
            return 0.0
            
        except Exception as e:
            logger.error(
                "duration_check_failed",
                error=str(e),
                file_path=file_path
            )
            return 0.0


# Dependency injection
_realtime_proxy_service: Optional[RealtimeProxyService] = None


async def get_realtime_proxy_service() -> RealtimeProxyService:
    """Get real-time proxy service instance"""
    global _realtime_proxy_service
    
    if _realtime_proxy_service is None:
        _realtime_proxy_service = RealtimeProxyService()
    
    return _realtime_proxy_service