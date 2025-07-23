"""Metaverse Manager Service

Central coordinator for all metaverse platform integrations and services.
Manages connections to various virtual worlds, VR/AR platforms, and blockchain services.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from ..core.config import settings
from .virtual_world_service import VirtualWorldService
from .vr_service import VRService
from .ar_service import ARService
from .avatar_service import AvatarService
from .spatial_service import SpatialService
from .blockchain_service import BlockchainService
from .cross_platform_service import CrossPlatformService

logger = logging.getLogger(__name__)

class MetaversePlatform:
    """Represents a connected metaverse platform"""
    
    def __init__(self, name: str, platform_type: str, config: Dict[str, Any]):
        self.name = name
        self.platform_type = platform_type  # 'virtual_world', 'vr', 'ar', 'blockchain'
        self.config = config
        self.status = "disconnected"
        self.last_ping = None
        self.capabilities = []
        self.active_sessions = 0
        self.error_count = 0
        
    async def connect(self) -> bool:
        """Connect to the platform"""
        try:
            # Platform-specific connection logic would go here
            logger.info(f"Connecting to {self.name} ({self.platform_type})")
            
            # Simulate connection
            await asyncio.sleep(0.1)
            
            self.status = "connected"
            self.last_ping = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.name}: {e}")
            self.status = "error"
            self.error_count += 1
            return False
    
    async def disconnect(self):
        """Disconnect from the platform"""
        logger.info(f"Disconnecting from {self.name}")
        self.status = "disconnected"
        self.active_sessions = 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Platform-specific health check logic
            await asyncio.sleep(0.05)
            
            if self.status == "connected":
                self.last_ping = datetime.utcnow()
                return {
                    "status": "healthy",
                    "last_ping": self.last_ping.isoformat(),
                    "active_sessions": self.active_sessions,
                    "capabilities": self.capabilities
                }
            else:
                return {
                    "status": "unhealthy",
                    "error_count": self.error_count
                }
                
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            self.error_count += 1
            return {
                "status": "error",
                "error": str(e),
                "error_count": self.error_count
            }

class MetaverseManager:
    """Central manager for all metaverse integrations"""
    
    def __init__(self):
        self.platforms: Dict[str, MetaversePlatform] = {}
        self.services: Dict[str, Any] = {}
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Initialize sub-services
        self.virtual_world_service = VirtualWorldService()
        self.vr_service = VRService()
        self.ar_service = ARService()
        self.avatar_service = AvatarService()
        self.spatial_service = SpatialService()
        self.blockchain_service = BlockchainService()
        self.cross_platform_service = CrossPlatformService()
        
        # Store services for easy access
        self.services = {
            "virtual_worlds": self.virtual_world_service,
            "vr": self.vr_service,
            "ar": self.ar_service,
            "avatars": self.avatar_service,
            "spatial": self.spatial_service,
            "blockchain": self.blockchain_service,
            "cross_platform": self.cross_platform_service
        }
    
    async def initialize(self):
        """Initialize all metaverse platforms and services"""
        logger.info("Initializing Metaverse Manager")
        
        try:
            # Initialize platform connections
            await self._initialize_platforms()
            
            # Initialize services
            await self._initialize_services()
            
            logger.info("Metaverse Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Metaverse Manager: {e}")
            raise
    
    async def _initialize_platforms(self):
        """Initialize connections to metaverse platforms"""
        
        # Virtual World Platforms
        virtual_worlds = {
            "unity": {
                "type": "virtual_world",
                "config": {"server_url": settings.UNITY_SERVER_URL}
            },
            "unreal": {
                "type": "virtual_world", 
                "config": {"server_url": settings.UNREAL_SERVER_URL}
            }
        }
        
        # Add platforms with API keys
        if settings.VRCHAT_SDK_KEY:
            virtual_worlds["vrchat"] = {
                "type": "virtual_world",
                "config": {"api_key": settings.VRCHAT_SDK_KEY}
            }
        
        if settings.HORIZON_WORLDS_TOKEN:
            virtual_worlds["horizon_worlds"] = {
                "type": "virtual_world",
                "config": {"token": settings.HORIZON_WORLDS_TOKEN}
            }
        
        if settings.ROBLOX_API_KEY:
            virtual_worlds["roblox"] = {
                "type": "virtual_world",
                "config": {"api_key": settings.ROBLOX_API_KEY}
            }
        
        # VR Platforms
        vr_platforms = {}
        if settings.OCULUS_APP_ID:
            vr_platforms["oculus"] = {
                "type": "vr",
                "config": {"app_id": settings.OCULUS_APP_ID}
            }
        
        if settings.STEAMVR_SDK_PATH:
            vr_platforms["steamvr"] = {
                "type": "vr",
                "config": {"sdk_path": settings.STEAMVR_SDK_PATH}
            }
        
        # AR Platforms
        ar_platforms = {}
        if settings.APPLE_ARKIT_TEAM_ID:
            ar_platforms["arkit"] = {
                "type": "ar",
                "config": {"team_id": settings.APPLE_ARKIT_TEAM_ID}
            }
        
        if settings.ANDROID_ARCORE_API_KEY:
            ar_platforms["arcore"] = {
                "type": "ar",
                "config": {"api_key": settings.ANDROID_ARCORE_API_KEY}
            }
        
        # Blockchain Platforms
        blockchain_platforms = {
            "ethereum": {
                "type": "blockchain",
                "config": {"rpc_url": settings.ETHEREUM_RPC_URL}
            },
            "polygon": {
                "type": "blockchain",
                "config": {"rpc_url": settings.POLYGON_RPC_URL}
            }
        }
        
        # Combine all platforms
        all_platforms = {**virtual_worlds, **vr_platforms, **ar_platforms, **blockchain_platforms}
        
        # Initialize platform instances
        for name, config in all_platforms.items():
            platform = MetaversePlatform(name, config["type"], config["config"])
            self.platforms[name] = platform
            
            # Attempt connection
            connected = await platform.connect()
            if connected:
                logger.info(f"Successfully connected to {name}")
            else:
                logger.warning(f"Failed to connect to {name}")
    
    async def _initialize_services(self):
        """Initialize all sub-services"""
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'initialize'):
                    await service.initialize()
                logger.info(f"Initialized {service_name} service")
            except Exception as e:
                logger.error(f"Failed to initialize {service_name} service: {e}")
    
    async def start_background_services(self):
        """Start background monitoring and maintenance tasks"""
        
        # Health check task
        health_check_task = asyncio.create_task(self._health_check_loop())
        self._background_tasks.append(health_check_task)
        
        # Platform monitoring task
        monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._background_tasks.append(monitoring_task)
        
        # Cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._background_tasks.append(cleanup_task)
        
        logger.info("Background services started")
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while not self._shutdown_event.is_set():
            try:
                for platform in self.platforms.values():
                    if platform.status == "connected":
                        await platform.health_check()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(10)
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                # Collect platform metrics
                await self._collect_platform_metrics()
                
                # Monitor resource usage
                await self._monitor_resources()
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while not self._shutdown_event.is_set():
            try:
                # Clean up expired sessions
                await self._cleanup_expired_sessions()
                
                # Clean up temporary files
                await self._cleanup_temp_files()
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)
    
    async def _collect_platform_metrics(self):
        """Collect metrics from all platforms"""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "platforms": {}
        }
        
        for name, platform in self.platforms.items():
            metrics["platforms"][name] = {
                "status": platform.status,
                "active_sessions": platform.active_sessions,
                "error_count": platform.error_count,
                "last_ping": platform.last_ping.isoformat() if platform.last_ping else None
            }
        
        # Store metrics (could send to monitoring service)
        logger.debug(f"Platform metrics: {json.dumps(metrics, indent=2)}")
    
    async def _monitor_resources(self):
        """Monitor system resources"""
        # Monitor CPU, memory, disk usage
        # This would typically use system monitoring libraries
        pass
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired user sessions"""
        # Implementation would clean up inactive sessions
        pass
    
    async def _cleanup_temp_files(self):
        """Clean up temporary files"""
        # Implementation would clean up temporary 3D assets, renders, etc.
        pass
    
    async def get_platform_status(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific platform"""
        platform = self.platforms.get(platform_name)
        if not platform:
            return None
        
        return await platform.health_check()
    
    async def get_all_platform_status(self) -> Dict[str, Any]:
        """Get status of all platforms"""
        status = {}
        
        for name, platform in self.platforms.items():
            status[name] = await platform.health_check()
        
        return status
    
    async def deploy_asset_to_platform(
        self, 
        asset_id: str, 
        platform_name: str, 
        deployment_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy a media asset to a specific metaverse platform"""
        
        platform = self.platforms.get(platform_name)
        if not platform:
            raise ValueError(f"Platform {platform_name} not found")
        
        if platform.status != "connected":
            raise RuntimeError(f"Platform {platform_name} is not connected")
        
        # Route to appropriate service based on platform type
        if platform.platform_type == "virtual_world":
            return await self.virtual_world_service.deploy_asset(
                asset_id, platform_name, deployment_config
            )
        elif platform.platform_type == "vr":
            return await self.vr_service.deploy_asset(
                asset_id, platform_name, deployment_config
            )
        elif platform.platform_type == "ar":
            return await self.ar_service.deploy_asset(
                asset_id, platform_name, deployment_config
            )
        elif platform.platform_type == "blockchain":
            return await self.blockchain_service.deploy_asset(
                asset_id, platform_name, deployment_config
            )
        else:
            raise ValueError(f"Unsupported platform type: {platform.platform_type}")
    
    async def create_cross_platform_asset(
        self, 
        asset_id: str, 
        target_platforms: List[str],
        optimization_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create cross-platform compatible versions of an asset"""
        
        return await self.cross_platform_service.create_cross_platform_asset(
            asset_id, target_platforms, optimization_settings
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Overall health check for the manager"""
        
        connected_platforms = sum(
            1 for p in self.platforms.values() 
            if p.status == "connected"
        )
        
        total_sessions = sum(
            p.active_sessions for p in self.platforms.values()
        )
        
        return {
            "status": "healthy" if connected_platforms > 0 else "degraded",
            "total_platforms": len(self.platforms),
            "connected_platforms": connected_platforms,
            "total_active_sessions": total_sessions,
            "background_tasks": len(self._background_tasks),
            "services": list(self.services.keys())
        }
    
    async def shutdown(self):
        """Shutdown the metaverse manager"""
        logger.info("Shutting down Metaverse Manager")
        
        # Signal shutdown to background tasks
        self._shutdown_event.set()
        
        # Wait for background tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Disconnect from all platforms
        for platform in self.platforms.values():
            await platform.disconnect()
        
        # Shutdown services
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'shutdown'):
                    await service.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {service_name}: {e}")
        
        logger.info("Metaverse Manager shutdown complete")