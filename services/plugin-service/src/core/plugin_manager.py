"""
Plugin Manager for MAMS Plugin Architecture
"""

import os
import sys
import asyncio
import importlib
import importlib.util
from typing import Dict, List, Optional, Type, Any, Tuple
from pathlib import Path
import json
import yaml
from datetime import datetime
import hashlib
import shutil
import zipfile
import tempfile
from dataclasses import asdict

from .plugin_base import (
    PluginInterface,
    PluginType,
    PluginStatus,
    PluginMetadata,
    PluginConfig,
    PluginContext,
    PluginResult,
    PluginEvent,
    PluginCapability
)
from ..core.logging import get_logger
from ..core.exceptions import PluginError
from ..db.models import Plugin as PluginModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

logger = get_logger(__name__)


class PluginManager:
    """Manages plugin lifecycle and execution"""
    
    def __init__(self, plugins_dir: str = "/app/plugins", db_session: AsyncSession = None):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(exist_ok=True)
        self.db_session = db_session
        self._plugins: Dict[str, PluginInterface] = {}
        self._plugin_modules: Dict[str, Any] = {}
        self._plugin_paths: Dict[str, Path] = {}
        self._loading_lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize plugin manager and load all enabled plugins"""
        logger.info("Initializing plugin manager", plugins_dir=str(self.plugins_dir))
        
        # Load plugins from database
        if self.db_session:
            await self._load_plugins_from_db()
        
        # Scan plugin directory
        await self.scan_plugins()
        
        logger.info(
            "Plugin manager initialized",
            loaded_plugins=len(self._plugins),
            active_plugins=len([p for p in self._plugins.values() if p.status == PluginStatus.ENABLED])
        )
    
    async def scan_plugins(self):
        """Scan plugin directory for available plugins"""
        logger.info("Scanning for plugins", directory=str(self.plugins_dir))
        
        async with self._loading_lock:
            for plugin_dir in self.plugins_dir.iterdir():
                if plugin_dir.is_dir() and not plugin_dir.name.startswith('_'):
                    manifest_path = plugin_dir / "plugin.json"
                    if manifest_path.exists():
                        try:
                            await self._load_plugin_from_directory(plugin_dir)
                        except Exception as e:
                            logger.error(
                                "Failed to load plugin",
                                plugin_dir=str(plugin_dir),
                                error=str(e)
                            )
    
    async def _load_plugin_from_directory(self, plugin_dir: Path):
        """Load a plugin from a directory"""
        manifest_path = plugin_dir / "plugin.json"
        
        # Read manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Create metadata
        metadata = PluginMetadata(**manifest['metadata'])
        
        # Load config
        config_path = plugin_dir / "config.yaml"
        config_data = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        config = PluginConfig(**config_data)
        
        # Load plugin module
        plugin_module_path = plugin_dir / "main.py"
        if not plugin_module_path.exists():
            raise PluginError(f"Plugin main.py not found in {plugin_dir}")
        
        # Import plugin module
        spec = importlib.util.spec_from_file_location(
            f"plugins.{metadata.id}",
            plugin_module_path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        
        # Find plugin class
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, PluginInterface) and 
                attr is not PluginInterface):
                plugin_class = attr
                break
        
        if not plugin_class:
            raise PluginError(f"No plugin class found in {plugin_module_path}")
        
        # Instantiate plugin
        plugin_instance = plugin_class(metadata, config)
        
        # Initialize plugin
        if await plugin_instance.initialize():
            plugin_instance.status = PluginStatus.ENABLED if config.enabled else PluginStatus.DISABLED
        else:
            plugin_instance.status = PluginStatus.ERROR
            logger.error("Plugin initialization failed", plugin_id=metadata.id)
        
        # Register plugin
        self._plugins[metadata.id] = plugin_instance
        self._plugin_modules[metadata.id] = module
        self._plugin_paths[metadata.id] = plugin_dir
        
        logger.info(
            "Plugin loaded",
            plugin_id=metadata.id,
            plugin_name=metadata.name,
            plugin_version=metadata.version,
            plugin_status=plugin_instance.status.value
        )
    
    async def install_plugin(self, plugin_package: bytes, filename: str) -> PluginMetadata:
        """Install a plugin from a package file"""
        logger.info("Installing plugin", filename=filename)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            package_path = temp_path / filename
            
            # Save package file
            with open(package_path, 'wb') as f:
                f.write(plugin_package)
            
            # Extract package
            if filename.endswith('.zip'):
                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
            else:
                raise PluginError(f"Unsupported package format: {filename}")
            
            # Find plugin manifest
            manifest_path = None
            for root, dirs, files in os.walk(temp_path):
                if 'plugin.json' in files:
                    manifest_path = Path(root) / 'plugin.json'
                    break
            
            if not manifest_path:
                raise PluginError("No plugin.json found in package")
            
            # Read manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            metadata = PluginMetadata(**manifest['metadata'])
            
            # Check if plugin already exists
            if metadata.id in self._plugins:
                raise PluginError(f"Plugin {metadata.id} already installed")
            
            # Validate plugin
            await self._validate_plugin_package(manifest_path.parent, manifest)
            
            # Copy to plugins directory
            plugin_dir = self.plugins_dir / metadata.id
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            
            shutil.copytree(manifest_path.parent, plugin_dir)
            
            # Load plugin
            await self._load_plugin_from_directory(plugin_dir)
            
            # Save to database
            if self.db_session:
                await self._save_plugin_to_db(metadata)
            
            logger.info(
                "Plugin installed successfully",
                plugin_id=metadata.id,
                plugin_name=metadata.name,
                plugin_version=metadata.version
            )
            
            return metadata
    
    async def _validate_plugin_package(self, plugin_dir: Path, manifest: Dict[str, Any]):
        """Validate plugin package structure and requirements"""
        # Check required files
        required_files = ['main.py', 'plugin.json']
        for req_file in required_files:
            if not (plugin_dir / req_file).exists():
                raise PluginError(f"Required file {req_file} not found")
        
        # Validate metadata
        required_fields = ['id', 'name', 'version', 'description', 'author']
        metadata = manifest.get('metadata', {})
        for field in required_fields:
            if field not in metadata:
                raise PluginError(f"Required metadata field '{field}' not found")
        
        # Check dependencies
        requirements_file = plugin_dir / 'requirements.txt'
        if requirements_file.exists():
            # TODO: Validate dependencies against allowed list
            pass
    
    async def uninstall_plugin(self, plugin_id: str):
        """Uninstall a plugin"""
        logger.info("Uninstalling plugin", plugin_id=plugin_id)
        
        if plugin_id not in self._plugins:
            raise PluginError(f"Plugin {plugin_id} not found")
        
        plugin = self._plugins[plugin_id]
        
        # Shutdown plugin
        await plugin.shutdown()
        
        # Remove from registry
        del self._plugins[plugin_id]
        del self._plugin_modules[plugin_id]
        
        # Remove plugin directory
        plugin_dir = self._plugin_paths.get(plugin_id)
        if plugin_dir and plugin_dir.exists():
            shutil.rmtree(plugin_dir)
            del self._plugin_paths[plugin_id]
        
        # Update database
        if self.db_session:
            await self._remove_plugin_from_db(plugin_id)
        
        logger.info("Plugin uninstalled", plugin_id=plugin_id)
    
    async def enable_plugin(self, plugin_id: str):
        """Enable a plugin"""
        if plugin_id not in self._plugins:
            raise PluginError(f"Plugin {plugin_id} not found")
        
        plugin = self._plugins[plugin_id]
        
        if plugin.status == PluginStatus.ENABLED:
            return
        
        # Initialize if needed
        if plugin.status in [PluginStatus.DISABLED, PluginStatus.ERROR]:
            if await plugin.initialize():
                plugin.status = PluginStatus.ENABLED
                plugin.config.enabled = True
                await self._update_plugin_status_in_db(plugin_id, PluginStatus.ENABLED)
                logger.info("Plugin enabled", plugin_id=plugin_id)
            else:
                plugin.status = PluginStatus.ERROR
                raise PluginError(f"Failed to enable plugin {plugin_id}")
    
    async def disable_plugin(self, plugin_id: str):
        """Disable a plugin"""
        if plugin_id not in self._plugins:
            raise PluginError(f"Plugin {plugin_id} not found")
        
        plugin = self._plugins[plugin_id]
        
        if plugin.status == PluginStatus.DISABLED:
            return
        
        # Shutdown plugin
        await plugin.shutdown()
        plugin.status = PluginStatus.DISABLED
        plugin.config.enabled = False
        
        await self._update_plugin_status_in_db(plugin_id, PluginStatus.DISABLED)
        logger.info("Plugin disabled", plugin_id=plugin_id)
    
    async def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Get a plugin instance"""
        return self._plugins.get(plugin_id)
    
    async def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInterface]:
        """Get all plugins of a specific type"""
        return [
            plugin for plugin in self._plugins.values()
            if plugin.get_type() == plugin_type and plugin.status == PluginStatus.ENABLED
        ]
    
    async def get_all_plugins(self) -> List[PluginInterface]:
        """Get all loaded plugins"""
        return list(self._plugins.values())
    
    async def execute_hook(
        self,
        hook_name: str,
        context: PluginContext,
        plugin_type: Optional[PluginType] = None,
        **kwargs
    ) -> List[Tuple[str, PluginResult]]:
        """Execute a hook across all enabled plugins"""
        results = []
        
        # Filter plugins
        plugins = self._plugins.values()
        if plugin_type:
            plugins = [p for p in plugins if p.get_type() == plugin_type]
        
        # Execute hook on each enabled plugin
        for plugin in plugins:
            if plugin.status == PluginStatus.ENABLED:
                try:
                    result = await plugin.execute_hook(hook_name, context, **kwargs)
                    results.append((plugin.metadata.id, result))
                except Exception as e:
                    logger.error(
                        "Plugin hook execution failed",
                        plugin_id=plugin.metadata.id,
                        hook_name=hook_name,
                        error=str(e)
                    )
                    results.append((
                        plugin.metadata.id,
                        PluginResult(success=False, error=str(e))
                    ))
        
        return results
    
    async def broadcast_event(self, event: PluginEvent) -> List[Tuple[str, List[PluginResult]]]:
        """Broadcast an event to all enabled plugins"""
        results = []
        
        for plugin in self._plugins.values():
            if plugin.status == PluginStatus.ENABLED:
                try:
                    plugin_results = await plugin.handle_event(event)
                    results.append((plugin.metadata.id, plugin_results))
                except Exception as e:
                    logger.error(
                        "Plugin event handling failed",
                        plugin_id=plugin.metadata.id,
                        event_type=event.event_type,
                        error=str(e)
                    )
        
        return results
    
    async def check_plugin_capability(self, plugin_id: str, capability: PluginCapability) -> bool:
        """Check if a plugin has a specific capability"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        return plugin.has_capability(capability)
    
    async def get_plugin_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all plugins"""
        health_status = {}
        
        for plugin_id, plugin in self._plugins.items():
            try:
                health_status[plugin_id] = {
                    'status': plugin.status.value,
                    'health': plugin.get_health_status(),
                    'metadata': asdict(plugin.metadata),
                    'enabled': plugin.config.enabled
                }
            except Exception as e:
                health_status[plugin_id] = {
                    'status': PluginStatus.ERROR.value,
                    'health': {'error': str(e)},
                    'metadata': asdict(plugin.metadata) if plugin else {},
                    'enabled': False
                }
        
        return health_status
    
    async def reload_plugin(self, plugin_id: str):
        """Reload a plugin"""
        logger.info("Reloading plugin", plugin_id=plugin_id)
        
        if plugin_id not in self._plugins:
            raise PluginError(f"Plugin {plugin_id} not found")
        
        # Disable plugin
        await self.disable_plugin(plugin_id)
        
        # Remove from modules
        if plugin_id in self._plugin_modules:
            module_name = f"plugins.{plugin_id}"
            if module_name in sys.modules:
                del sys.modules[module_name]
        
        # Reload from directory
        plugin_dir = self._plugin_paths.get(plugin_id)
        if plugin_dir and plugin_dir.exists():
            await self._load_plugin_from_directory(plugin_dir)
            
            # Re-enable if it was enabled before
            if self._plugins[plugin_id].config.enabled:
                await self.enable_plugin(plugin_id)
        
        logger.info("Plugin reloaded", plugin_id=plugin_id)
    
    async def _load_plugins_from_db(self):
        """Load plugin information from database"""
        try:
            result = await self.db_session.execute(
                select(PluginModel).where(PluginModel.is_active == True)
            )
            plugins = result.scalars().all()
            
            for plugin_record in plugins:
                # Plugin loading will happen in scan_plugins
                logger.debug(
                    "Found plugin in database",
                    plugin_id=plugin_record.plugin_id,
                    status=plugin_record.status
                )
        except Exception as e:
            logger.error("Failed to load plugins from database", error=str(e))
    
    async def _save_plugin_to_db(self, metadata: PluginMetadata):
        """Save plugin information to database"""
        try:
            plugin_record = PluginModel(
                plugin_id=metadata.id,
                name=metadata.name,
                version=metadata.version,
                description=metadata.description,
                author=metadata.author,
                status=PluginStatus.INSTALLED.value,
                metadata=asdict(metadata),
                is_active=True
            )
            
            self.db_session.add(plugin_record)
            await self.db_session.commit()
        except Exception as e:
            logger.error("Failed to save plugin to database", error=str(e))
            await self.db_session.rollback()
    
    async def _update_plugin_status_in_db(self, plugin_id: str, status: PluginStatus):
        """Update plugin status in database"""
        try:
            await self.db_session.execute(
                update(PluginModel)
                .where(PluginModel.plugin_id == plugin_id)
                .values(status=status.value, updated_at=datetime.utcnow())
            )
            await self.db_session.commit()
        except Exception as e:
            logger.error("Failed to update plugin status in database", error=str(e))
            await self.db_session.rollback()
    
    async def _remove_plugin_from_db(self, plugin_id: str):
        """Remove plugin from database"""
        try:
            await self.db_session.execute(
                update(PluginModel)
                .where(PluginModel.plugin_id == plugin_id)
                .values(is_active=False, updated_at=datetime.utcnow())
            )
            await self.db_session.commit()
        except Exception as e:
            logger.error("Failed to remove plugin from database", error=str(e))
            await self.db_session.rollback()
    
    async def cleanup(self):
        """Cleanup plugin manager resources"""
        logger.info("Cleaning up plugin manager")
        
        # Shutdown all plugins
        for plugin_id, plugin in list(self._plugins.items()):
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(
                    "Error shutting down plugin",
                    plugin_id=plugin_id,
                    error=str(e)
                )
        
        self._plugins.clear()
        self._plugin_modules.clear()
        self._plugin_paths.clear()