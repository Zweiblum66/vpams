"""
Plugin Loader for MAMS Plugin Architecture
"""

import os
import sys
import ast
import importlib.util
from typing import Dict, List, Optional, Type, Any, Tuple
from pathlib import Path
import subprocess
import venv
import shutil
import tempfile
import hashlib
import json
from datetime import datetime

from .plugin_base import PluginInterface, PluginMetadata, PluginConfig
from ..core.logging import get_logger
from ..core.exceptions import PluginError

logger = get_logger(__name__)


class PluginSandbox:
    """Sandbox environment for plugin execution"""
    
    def __init__(self, plugin_id: str, sandbox_dir: str = "/app/sandboxes"):
        self.plugin_id = plugin_id
        self.sandbox_dir = Path(sandbox_dir) / plugin_id
        self.venv_path = self.sandbox_dir / "venv"
        self.plugin_path = self.sandbox_dir / "plugin"
    
    def create(self):
        """Create sandbox environment"""
        logger.info("Creating sandbox", plugin_id=self.plugin_id)
        
        # Create directories
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.plugin_path.mkdir(exist_ok=True)
        
        # Create virtual environment
        venv.create(self.venv_path, with_pip=True)
        
        # Get pip path
        pip_path = self.venv_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = self.venv_path / "Scripts" / "pip.exe"
        
        # Install base requirements
        base_requirements = [
            "pydantic>=2.0.0",
            "aiohttp>=3.8.0",
            "asyncio>=3.4.3"
        ]
        
        for req in base_requirements:
            subprocess.run(
                [str(pip_path), "install", req],
                check=True,
                capture_output=True
            )
        
        logger.info("Sandbox created", plugin_id=self.plugin_id)
    
    def install_requirements(self, requirements_file: Path):
        """Install plugin requirements in sandbox"""
        if not requirements_file.exists():
            return
        
        pip_path = self.venv_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = self.venv_path / "Scripts" / "pip.exe"
        
        # Validate requirements
        with open(requirements_file, 'r') as f:
            requirements = f.read().splitlines()
        
        allowed_packages = self._get_allowed_packages()
        
        for req in requirements:
            package_name = req.split('==')[0].split('>=')[0].split('<=')[0].strip()
            if package_name not in allowed_packages:
                raise PluginError(f"Package {package_name} is not allowed")
        
        # Install requirements
        subprocess.run(
            [str(pip_path), "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True
        )
    
    def _get_allowed_packages(self) -> List[str]:
        """Get list of allowed packages for plugins"""
        return [
            # Data processing
            "numpy", "pandas", "scipy", "scikit-learn",
            # Image processing
            "pillow", "opencv-python", "imageio",
            # Audio processing
            "librosa", "soundfile", "pydub",
            # Video processing
            "moviepy", "ffmpeg-python",
            # Web frameworks
            "requests", "aiohttp", "httpx",
            # Database
            "sqlalchemy", "pymongo", "redis",
            # Utilities
            "pyyaml", "jsonschema", "python-dateutil",
            # ML/AI
            "tensorflow", "torch", "transformers"
        ]
    
    def cleanup(self):
        """Clean up sandbox environment"""
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)
            logger.info("Sandbox cleaned up", plugin_id=self.plugin_id)


class PluginValidator:
    """Validates plugin code for security and compatibility"""
    
    @staticmethod
    def validate_plugin_code(plugin_path: Path) -> Tuple[bool, List[str]]:
        """Validate plugin code for security issues"""
        issues = []
        
        # Check all Python files
        for py_file in plugin_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Parse AST
                tree = ast.parse(content)
                
                # Check for dangerous imports
                dangerous_imports = [
                    'os', 'subprocess', 'eval', 'exec', '__import__',
                    'compile', 'open', 'file', 'input', 'raw_input'
                ]
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in dangerous_imports:
                                issues.append(
                                    f"Dangerous import '{alias.name}' in {py_file}"
                                )
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module in dangerous_imports:
                            issues.append(
                                f"Dangerous import from '{node.module}' in {py_file}"
                            )
                    
                    # Check for eval/exec calls
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in ['eval', 'exec', 'compile']:
                                issues.append(
                                    f"Dangerous function '{node.func.id}' in {py_file}"
                                )
            
            except Exception as e:
                issues.append(f"Failed to parse {py_file}: {str(e)}")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_plugin_manifest(manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate plugin manifest"""
        issues = []
        
        # Check required fields
        required_fields = {
            'metadata': {
                'id': str,
                'name': str,
                'version': str,
                'description': str,
                'author': str
            }
        }
        
        for field, field_type in required_fields.items():
            if field not in manifest:
                issues.append(f"Missing required field: {field}")
            elif isinstance(field_type, dict):
                for subfield, subfield_type in field_type.items():
                    if subfield not in manifest[field]:
                        issues.append(f"Missing required field: {field}.{subfield}")
                    elif not isinstance(manifest[field][subfield], subfield_type):
                        issues.append(
                            f"Invalid type for {field}.{subfield}: "
                            f"expected {subfield_type.__name__}"
                        )
        
        # Validate version format
        if 'metadata' in manifest and 'version' in manifest['metadata']:
            version = manifest['metadata']['version']
            if not all(part.isdigit() for part in version.split('.')):
                issues.append(f"Invalid version format: {version}")
        
        return len(issues) == 0, issues


class PluginLoader:
    """Loads and manages plugin modules"""
    
    def __init__(self, use_sandbox: bool = True):
        self.use_sandbox = use_sandbox
        self._loaded_modules: Dict[str, Any] = {}
        self._sandboxes: Dict[str, PluginSandbox] = {}
    
    async def load_plugin(
        self,
        plugin_path: Path,
        metadata: PluginMetadata,
        config: PluginConfig
    ) -> PluginInterface:
        """Load a plugin from path"""
        logger.info(
            "Loading plugin",
            plugin_id=metadata.id,
            plugin_path=str(plugin_path)
        )
        
        # Validate plugin code
        valid, issues = PluginValidator.validate_plugin_code(plugin_path)
        if not valid:
            raise PluginError(f"Plugin validation failed: {', '.join(issues)}")
        
        # Create sandbox if enabled
        if self.use_sandbox:
            sandbox = PluginSandbox(metadata.id)
            sandbox.create()
            
            # Copy plugin to sandbox
            shutil.copytree(plugin_path, sandbox.plugin_path, dirs_exist_ok=True)
            
            # Install requirements
            requirements_file = sandbox.plugin_path / "requirements.txt"
            if requirements_file.exists():
                sandbox.install_requirements(requirements_file)
            
            self._sandboxes[metadata.id] = sandbox
            plugin_path = sandbox.plugin_path
        
        # Load plugin module
        main_module_path = plugin_path / "main.py"
        if not main_module_path.exists():
            raise PluginError(f"Plugin main.py not found in {plugin_path}")
        
        # Import module
        spec = importlib.util.spec_from_file_location(
            f"plugins.{metadata.id}",
            main_module_path
        )
        
        if spec is None or spec.loader is None:
            raise PluginError(f"Failed to load plugin module from {main_module_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Add plugin path to module search path
        if str(plugin_path) not in sys.path:
            sys.path.insert(0, str(plugin_path))
        
        try:
            spec.loader.exec_module(module)
        finally:
            # Remove from path
            if str(plugin_path) in sys.path:
                sys.path.remove(str(plugin_path))
        
        # Find plugin class
        plugin_class = self._find_plugin_class(module)
        if not plugin_class:
            raise PluginError(f"No plugin class found in {main_module_path}")
        
        # Create plugin instance
        plugin_instance = plugin_class(metadata, config)
        
        # Store module reference
        self._loaded_modules[metadata.id] = module
        
        logger.info(
            "Plugin loaded successfully",
            plugin_id=metadata.id,
            plugin_class=plugin_class.__name__
        )
        
        return plugin_instance
    
    def _find_plugin_class(self, module: Any) -> Optional[Type[PluginInterface]]:
        """Find the plugin class in a module"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, PluginInterface) and 
                attr is not PluginInterface and
                not attr.__name__.startswith('_')):
                return attr
        return None
    
    def unload_plugin(self, plugin_id: str):
        """Unload a plugin module"""
        logger.info("Unloading plugin", plugin_id=plugin_id)
        
        # Remove module
        if plugin_id in self._loaded_modules:
            module_name = f"plugins.{plugin_id}"
            
            # Remove from sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            # Remove all submodules
            to_remove = []
            for name in sys.modules:
                if name.startswith(f"{module_name}."):
                    to_remove.append(name)
            
            for name in to_remove:
                del sys.modules[name]
            
            del self._loaded_modules[plugin_id]
        
        # Cleanup sandbox
        if plugin_id in self._sandboxes:
            self._sandboxes[plugin_id].cleanup()
            del self._sandboxes[plugin_id]
        
        logger.info("Plugin unloaded", plugin_id=plugin_id)
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin IDs"""
        return list(self._loaded_modules.keys())
    
    def calculate_plugin_hash(self, plugin_path: Path) -> str:
        """Calculate hash of plugin files for integrity check"""
        hasher = hashlib.sha256()
        
        for file_path in sorted(plugin_path.rglob("*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def verify_plugin_signature(self, plugin_path: Path, signature: str) -> bool:
        """Verify plugin signature (placeholder for actual implementation)"""
        # TODO: Implement actual signature verification
        # This would involve public key cryptography
        return True
    
    def cleanup_all(self):
        """Clean up all loaded plugins and sandboxes"""
        logger.info("Cleaning up all plugins")
        
        # Unload all plugins
        for plugin_id in list(self._loaded_modules.keys()):
            self.unload_plugin(plugin_id)
        
        # Clean up any remaining sandboxes
        for plugin_id, sandbox in list(self._sandboxes.items()):
            sandbox.cleanup()
        
        self._sandboxes.clear()
    
    async def validate_plugin_code(self, code: str) -> Dict[str, Any]:
        """Validate plugin code using AST parsing"""
        try:
            # Parse the code
            tree = ast.parse(code)
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check for dangerous imports
            dangerous_imports = [
                'os', 'subprocess', 'sys', 'shutil', 'socket', 
                'urllib', 'requests', 'ftplib', 'telnetlib',
                '__import__', 'eval', 'exec', 'compile'
            ]
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in dangerous_imports:
                            validation_result["warnings"].append(
                                f"Potentially dangerous import: {alias.name}"
                            )
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module in dangerous_imports:
                        validation_result["warnings"].append(
                            f"Potentially dangerous import from: {node.module}"
                        )
                
                elif isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Name) and 
                        node.func.id in ['eval', 'exec', 'compile']):
                        validation_result["errors"].append(
                            f"Dangerous function call: {node.func.id}"
                        )
                        validation_result["valid"] = False
            
            # Check for required plugin class
            has_plugin_class = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class inherits from a plugin base class
                    for base in node.bases:
                        if isinstance(base, ast.Name) and 'Plugin' in base.id:
                            has_plugin_class = True
                            break
            
            if not has_plugin_class:
                validation_result["errors"].append(
                    "No plugin class found. Plugin must inherit from a base plugin class."
                )
                validation_result["valid"] = False
            
            return validation_result
            
        except SyntaxError as e:
            return {
                "valid": False,
                "errors": [f"Syntax error: {str(e)}"],
                "warnings": []
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    async def validate_plugin_config(self, config_yaml: str) -> Dict[str, Any]:
        """Validate plugin configuration"""
        try:
            import yaml
            config = yaml.safe_load(config_yaml)
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check required fields
            if not isinstance(config, dict):
                validation_result["errors"].append("Configuration must be a valid YAML object")
                validation_result["valid"] = False
                return validation_result
            
            # Check for enabled field
            if 'enabled' not in config:
                validation_result["warnings"].append("Missing 'enabled' field, defaulting to true")
            elif not isinstance(config['enabled'], bool):
                validation_result["errors"].append("'enabled' field must be a boolean")
                validation_result["valid"] = False
            
            # Check settings
            if 'settings' in config and not isinstance(config['settings'], dict):
                validation_result["errors"].append("'settings' field must be an object")
                validation_result["valid"] = False
            
            # Check capabilities
            if 'capabilities' in config:
                if not isinstance(config['capabilities'], list):
                    validation_result["errors"].append("'capabilities' field must be a list")
                    validation_result["valid"] = False
                else:
                    valid_capabilities = [
                        'read_assets', 'write_assets', 'delete_assets',
                        'read_metadata', 'write_metadata',
                        'execute_workflows', 'manage_users',
                        'access_api', 'send_notifications'
                    ]
                    for capability in config['capabilities']:
                        if capability not in valid_capabilities:
                            validation_result["warnings"].append(
                                f"Unknown capability: {capability}"
                            )
            
            return validation_result
            
        except yaml.YAMLError as e:
            return {
                "valid": False,
                "errors": [f"YAML parsing error: {str(e)}"],
                "warnings": []
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Configuration validation error: {str(e)}"],
                "warnings": []
            }
    
    async def validate_plugin_manifest(self, manifest_json: str) -> Dict[str, Any]:
        """Validate plugin manifest (plugin.json)"""
        try:
            manifest = json.loads(manifest_json)
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check required top-level fields
            required_fields = ['metadata']
            for field in required_fields:
                if field not in manifest:
                    validation_result["errors"].append(f"Missing required field: {field}")
                    validation_result["valid"] = False
            
            # Check metadata fields
            if 'metadata' in manifest:
                metadata = manifest['metadata']
                required_metadata = ['id', 'name', 'version', 'description', 'author']
                for field in required_metadata:
                    if field not in metadata:
                        validation_result["errors"].append(
                            f"Missing required metadata field: {field}"
                        )
                        validation_result["valid"] = False
                
                # Validate version format
                if 'version' in metadata:
                    version = metadata['version']
                    if not isinstance(version, str) or not all(
                        part.isdigit() for part in version.split('.')
                    ):
                        validation_result["errors"].append(
                            f"Invalid version format: {version}. Use semantic versioning (e.g., 1.0.0)"
                        )
                        validation_result["valid"] = False
                
                # Validate plugin ID format
                if 'id' in metadata:
                    plugin_id = metadata['id']
                    if not isinstance(plugin_id, str) or not plugin_id.replace('-', '').replace('_', '').isalnum():
                        validation_result["errors"].append(
                            f"Invalid plugin ID format: {plugin_id}. Use alphanumeric characters, hyphens, and underscores only."
                        )
                        validation_result["valid"] = False
            
            # Check requirements
            if 'requirements' in manifest:
                requirements = manifest['requirements']
                if 'python' in requirements:
                    python_version = requirements['python']
                    if not isinstance(python_version, str):
                        validation_result["warnings"].append(
                            "Python version requirement should be a string"
                        )
                
                if 'dependencies' in requirements:
                    if not isinstance(requirements['dependencies'], list):
                        validation_result["errors"].append(
                            "Dependencies must be a list"
                        )
                        validation_result["valid"] = False
            
            return validation_result
            
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "errors": [f"JSON parsing error: {str(e)}"],
                "warnings": []
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Manifest validation error: {str(e)}"],
                "warnings": []
            }