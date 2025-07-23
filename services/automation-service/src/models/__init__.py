"""Models module for Broadcast Automation Service"""

from .schemas import (
    # Device schemas
    DeviceBase,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceStatus,
    DevicePresetBase,
    DevicePresetCreate,
    DevicePresetUpdate,
    DevicePresetResponse,
    # Macro schemas
    MacroBase,
    MacroCreate,
    MacroUpdate,
    MacroResponse,
    MacroExecuteRequest,
    MacroExecutionResponse,
    # Show schemas
    ShowBase,
    ShowCreate,
    ShowUpdate,
    ShowResponse,
    ShowCueBase,
    ShowCueCreate,
    ShowCueUpdate,
    ShowCueResponse,
    # Command schemas
    DeviceCommand,
    CommandResponse,
    # Control schemas
    PTZControl,
    FocusControl,
    IrisControl,
    AudioFaderControl,
    SwitcherControl,
    # Schedule schemas
    ScheduledExecutionBase,
    ScheduledExecutionCreate,
    ScheduledExecutionUpdate,
    ScheduledExecutionResponse,
    # Device group schemas
    DeviceGroupBase,
    DeviceGroupCreate,
    DeviceGroupUpdate,
    DeviceGroupResponse,
    # Emergency schemas
    EmergencyOverrideRequest,
    EmergencyOverrideResponse,
    # Discovery schemas
    DiscoveryRequest,
    DiscoveredDevice,
    # WebSocket schemas
    WSMessage,
    WSResponse,
    # Pagination schemas
    PaginationParams,
    PaginatedResponse,
)

__all__ = [
    # Device schemas
    "DeviceBase",
    "DeviceCreate",
    "DeviceUpdate",
    "DeviceResponse",
    "DeviceStatus",
    "DevicePresetBase",
    "DevicePresetCreate",
    "DevicePresetUpdate",
    "DevicePresetResponse",
    # Macro schemas
    "MacroBase",
    "MacroCreate",
    "MacroUpdate",
    "MacroResponse",
    "MacroExecuteRequest",
    "MacroExecutionResponse",
    # Show schemas
    "ShowBase",
    "ShowCreate",
    "ShowUpdate",
    "ShowResponse",
    "ShowCueBase",
    "ShowCueCreate",
    "ShowCueUpdate",
    "ShowCueResponse",
    # Command schemas
    "DeviceCommand",
    "CommandResponse",
    # Control schemas
    "PTZControl",
    "FocusControl",
    "IrisControl",
    "AudioFaderControl",
    "SwitcherControl",
    # Schedule schemas
    "ScheduledExecutionBase",
    "ScheduledExecutionCreate",
    "ScheduledExecutionUpdate",
    "ScheduledExecutionResponse",
    # Device group schemas
    "DeviceGroupBase",
    "DeviceGroupCreate",
    "DeviceGroupUpdate",
    "DeviceGroupResponse",
    # Emergency schemas
    "EmergencyOverrideRequest",
    "EmergencyOverrideResponse",
    # Discovery schemas
    "DiscoveryRequest",
    "DiscoveredDevice",
    # WebSocket schemas
    "WSMessage",
    "WSResponse",
    # Pagination schemas
    "PaginationParams",
    "PaginatedResponse",
]