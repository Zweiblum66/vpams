"""API module for Broadcast Automation Service"""

from .routes import (
    device_router,
    camera_router,
    switcher_router,
    audio_router,
    macro_router,
    show_router,
    control_router,
)

__all__ = [
    "device_router",
    "camera_router",
    "switcher_router",
    "audio_router",
    "macro_router",
    "show_router",
    "control_router",
]