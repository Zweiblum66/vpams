"""Database module for Broadcast Automation Service"""

from .base import Base, get_db, get_db_context, init_db, close_db
from .models import (
    Device,
    DevicePreset,
    Macro,
    MacroExecution,
    Show,
    ShowCue,
    CommandLog,
    ScheduledExecution,
    DeviceGroup,
    EmergencyOverride,
    DeviceType,
    DeviceStatus,
    ConnectionType,
    MacroStatus,
    CueStatus,
)

__all__ = [
    # Base
    "Base",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    # Models
    "Device",
    "DevicePreset",
    "Macro",
    "MacroExecution",
    "Show",
    "ShowCue",
    "CommandLog",
    "ScheduledExecution",
    "DeviceGroup",
    "EmergencyOverride",
    # Enums
    "DeviceType",
    "DeviceStatus",
    "ConnectionType",
    "MacroStatus",
    "CueStatus",
]