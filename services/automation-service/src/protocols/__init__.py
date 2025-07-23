"""Protocol adapters for device control"""

from .base import (
    BaseProtocolAdapter,
    ProtocolCapability,
    ConnectionState,
    ProtocolRegistry,
)

# Import specific protocol adapters when implemented
# from .visca import ViscaProtocolAdapter
# from .ross_talk import RossTalkProtocolAdapter
# from .ember_plus import EmberPlusProtocolAdapter
# from .ndi import NDIProtocolAdapter

__all__ = [
    "BaseProtocolAdapter",
    "ProtocolCapability",
    "ConnectionState",
    "ProtocolRegistry",
]

# Register protocol adapters when implemented
# ProtocolRegistry.register("visca", ViscaProtocolAdapter)
# ProtocolRegistry.register("ross_talk", RossTalkProtocolAdapter)
# ProtocolRegistry.register("ember+", EmberPlusProtocolAdapter)
# ProtocolRegistry.register("ndi", NDIProtocolAdapter)