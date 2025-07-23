"""
Plugin Service Exceptions
"""

from typing import Optional, Dict, Any, List


class PluginError(Exception):
    """Base exception for plugin errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "PLUGIN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class PluginNotFoundError(PluginError):
    """Plugin not found"""
    
    def __init__(self, plugin_id: str):
        super().__init__(
            f"Plugin '{plugin_id}' not found",
            error_code="PLUGIN_NOT_FOUND",
            status_code=404,
            details={"plugin_id": plugin_id}
        )


class PluginLoadError(PluginError):
    """Plugin failed to load"""
    
    def __init__(self, plugin_id: str, reason: str):
        super().__init__(
            f"Failed to load plugin '{plugin_id}': {reason}",
            error_code="PLUGIN_LOAD_ERROR",
            status_code=500,
            details={"plugin_id": plugin_id, "reason": reason}
        )


class PluginValidationError(PluginError):
    """Plugin validation failed"""
    
    def __init__(self, plugin_id: str, issues: List[str]):
        super().__init__(
            f"Plugin '{plugin_id}' validation failed",
            error_code="PLUGIN_VALIDATION_ERROR",
            status_code=400,
            details={"plugin_id": plugin_id, "issues": issues}
        )


class PluginExecutionError(PluginError):
    """Plugin execution failed"""
    
    def __init__(self, plugin_id: str, operation: str, reason: str):
        super().__init__(
            f"Plugin '{plugin_id}' failed during {operation}: {reason}",
            error_code="PLUGIN_EXECUTION_ERROR",
            status_code=500,
            details={
                "plugin_id": plugin_id,
                "operation": operation,
                "reason": reason
            }
        )


class PluginPermissionError(PluginError):
    """Plugin lacks required permission"""
    
    def __init__(self, plugin_id: str, capability: str):
        super().__init__(
            f"Plugin '{plugin_id}' lacks capability: {capability}",
            error_code="PLUGIN_PERMISSION_ERROR",
            status_code=403,
            details={
                "plugin_id": plugin_id,
                "required_capability": capability
            }
        )


class PluginTimeoutError(PluginError):
    """Plugin operation timed out"""
    
    def __init__(self, plugin_id: str, operation: str, timeout: int):
        super().__init__(
            f"Plugin '{plugin_id}' timed out during {operation} (timeout: {timeout}s)",
            error_code="PLUGIN_TIMEOUT",
            status_code=504,
            details={
                "plugin_id": plugin_id,
                "operation": operation,
                "timeout": timeout
            }
        )


class PluginVersionError(PluginError):
    """Plugin version incompatible"""
    
    def __init__(self, plugin_id: str, plugin_version: str, required_version: str):
        super().__init__(
            f"Plugin '{plugin_id}' version {plugin_version} incompatible with required version {required_version}",
            error_code="PLUGIN_VERSION_ERROR",
            status_code=400,
            details={
                "plugin_id": plugin_id,
                "plugin_version": plugin_version,
                "required_version": required_version
            }
        )


class PluginDependencyError(PluginError):
    """Plugin dependency not satisfied"""
    
    def __init__(self, plugin_id: str, dependency: str):
        super().__init__(
            f"Plugin '{plugin_id}' dependency not satisfied: {dependency}",
            error_code="PLUGIN_DEPENDENCY_ERROR",
            status_code=424,
            details={
                "plugin_id": plugin_id,
                "missing_dependency": dependency
            }
        )


class PluginConfigError(PluginError):
    """Plugin configuration error"""
    
    def __init__(self, plugin_id: str, config_error: str):
        super().__init__(
            f"Plugin '{plugin_id}' configuration error: {config_error}",
            error_code="PLUGIN_CONFIG_ERROR",
            status_code=400,
            details={
                "plugin_id": plugin_id,
                "config_error": config_error
            }
        )