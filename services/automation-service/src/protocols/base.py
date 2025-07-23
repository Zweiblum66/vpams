"""Base protocol adapter for device control"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import logging
from enum import Enum

from ..models.schemas import DeviceStatus, CommandResponse
from ..db.models import Device, DeviceType, ConnectionType


logger = logging.getLogger(__name__)


class ProtocolCapability(str, Enum):
    """Protocol capabilities"""
    BIDIRECTIONAL = "bidirectional"
    STATUS_POLLING = "status_polling"
    EVENT_SUBSCRIPTION = "event_subscription"
    BATCH_COMMANDS = "batch_commands"
    SECURE_CONNECTION = "secure_connection"
    AUTO_RECONNECT = "auto_reconnect"
    COMMAND_QUEUE = "command_queue"
    REAL_TIME = "real_time"


class ConnectionState(str, Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class BaseProtocolAdapter(ABC):
    """Base class for all protocol adapters"""
    
    def __init__(self, device: Device):
        """Initialize protocol adapter
        
        Args:
            device: Device model instance
        """
        self.device = device
        self.connection_state = ConnectionState.DISCONNECTED
        self.last_error: Optional[str] = None
        self.last_communication: Optional[datetime] = None
        self.capabilities: List[ProtocolCapability] = []
        self._connection = None
        self._lock = asyncio.Lock()
        self._command_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Get protocol name"""
        pass
        
    @property
    @abstractmethod
    def supported_device_types(self) -> List[DeviceType]:
        """Get supported device types"""
        pass
        
    @property
    @abstractmethod
    def supported_connection_types(self) -> List[ConnectionType]:
        """Get supported connection types"""
        pass
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to device
        
        Returns:
            bool: True if connected successfully
        """
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from device"""
        pass
        
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to device
        
        Returns:
            bool: True if connected
        """
        pass
        
    @abstractmethod
    async def send_command(
        self,
        command: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> CommandResponse:
        """Send command to device
        
        Args:
            command: Command name
            parameters: Command parameters
            timeout: Command timeout in seconds
            
        Returns:
            CommandResponse: Command execution result
        """
        pass
        
    @abstractmethod
    async def get_status(self) -> DeviceStatus:
        """Get current device status
        
        Returns:
            DeviceStatus: Current device status
        """
        pass
        
    @abstractmethod
    async def get_capabilities(self) -> List[str]:
        """Get device capabilities
        
        Returns:
            List[str]: List of capability names
        """
        pass
        
    async def initialize(self) -> None:
        """Initialize protocol adapter"""
        self._running = True
        
        # Start command processor if supported
        if ProtocolCapability.COMMAND_QUEUE in self.capabilities:
            task = asyncio.create_task(self._process_command_queue())
            self._tasks.append(task)
            
        # Start heartbeat if supported
        if ProtocolCapability.STATUS_POLLING in self.capabilities:
            task = asyncio.create_task(self._heartbeat_loop())
            self._tasks.append(task)
            
    async def shutdown(self) -> None:
        """Shutdown protocol adapter"""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Disconnect
        await self.disconnect()
        
    async def _process_command_queue(self) -> None:
        """Process queued commands"""
        while self._running:
            try:
                # Get command from queue
                command_data = await asyncio.wait_for(
                    self._command_queue.get(),
                    timeout=1.0
                )
                
                # Send command
                await self.send_command(**command_data)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Command queue error: {e}")
                
    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop for connection monitoring"""
        while self._running:
            try:
                if await self.is_connected():
                    # Get status
                    status = await self.get_status()
                    self.last_communication = datetime.utcnow()
                    
                # Wait for next heartbeat
                await asyncio.sleep(self.device.protocol_config.get("heartbeat_interval", 10))
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self.last_error = str(e)
                
                # Attempt reconnection if supported
                if ProtocolCapability.AUTO_RECONNECT in self.capabilities:
                    await self._attempt_reconnect()
                    
    async def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to device"""
        if self.connection_state == ConnectionState.RECONNECTING:
            return
            
        self.connection_state = ConnectionState.RECONNECTING
        max_retries = self.device.protocol_config.get("max_reconnect_attempts", 5)
        retry_delay = self.device.protocol_config.get("reconnect_delay", 5)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Reconnection attempt {attempt + 1}/{max_retries} for {self.device.name}")
                
                # Disconnect first
                await self.disconnect()
                
                # Wait before reconnecting
                await asyncio.sleep(retry_delay)
                
                # Attempt connection
                if await self.connect():
                    logger.info(f"Reconnected to {self.device.name}")
                    return
                    
            except Exception as e:
                logger.error(f"Reconnection error: {e}")
                
        # Failed to reconnect
        self.connection_state = ConnectionState.ERROR
        self.last_error = "Failed to reconnect after maximum attempts"
        
    def validate_command(self, command: str) -> bool:
        """Validate if command is supported
        
        Args:
            command: Command name
            
        Returns:
            bool: True if command is supported
        """
        return command in self.device.supported_commands
        
    def validate_parameters(
        self,
        command: str,
        parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate command parameters
        
        Args:
            command: Command name
            parameters: Command parameters
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Base implementation - override in specific adapters
        return True, None
        
    async def queue_command(
        self,
        command: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> None:
        """Queue command for execution
        
        Args:
            command: Command name
            parameters: Command parameters
            timeout: Command timeout
        """
        if ProtocolCapability.COMMAND_QUEUE not in self.capabilities:
            raise NotImplementedError("Command queuing not supported")
            
        await self._command_queue.put({
            "command": command,
            "parameters": parameters,
            "timeout": timeout
        })
        
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information
        
        Returns:
            Dict[str, Any]: Connection information
        """
        return {
            "protocol": self.protocol_name,
            "state": self.connection_state.value,
            "last_communication": self.last_communication.isoformat() if self.last_communication else None,
            "last_error": self.last_error,
            "capabilities": [cap.value for cap in self.capabilities],
            "queue_size": self._command_queue.qsize() if hasattr(self, "_command_queue") else 0,
        }
        
    @staticmethod
    def parse_connection_string(connection_string: str) -> Dict[str, Any]:
        """Parse connection string into components
        
        Args:
            connection_string: Connection string (e.g., "tcp://192.168.1.1:9000")
            
        Returns:
            Dict[str, Any]: Parsed connection parameters
        """
        # Base implementation - override for specific protocols
        parts = connection_string.split("://")
        if len(parts) != 2:
            raise ValueError("Invalid connection string format")
            
        protocol = parts[0]
        address = parts[1]
        
        # Parse address
        if ":" in address:
            host, port = address.rsplit(":", 1)
            return {
                "protocol": protocol,
                "host": host,
                "port": int(port)
            }
        else:
            return {
                "protocol": protocol,
                "host": address,
                "port": None
            }


class ProtocolRegistry:
    """Registry for protocol adapters"""
    
    _adapters: Dict[str, type] = {}
    
    @classmethod
    def register(cls, protocol_name: str, adapter_class: type) -> None:
        """Register protocol adapter
        
        Args:
            protocol_name: Protocol name
            adapter_class: Adapter class
        """
        if not issubclass(adapter_class, BaseProtocolAdapter):
            raise TypeError("Adapter must inherit from BaseProtocolAdapter")
            
        cls._adapters[protocol_name.lower()] = adapter_class
        logger.info(f"Registered protocol adapter: {protocol_name}")
        
    @classmethod
    def get_adapter(cls, protocol_name: str, device: Device) -> BaseProtocolAdapter:
        """Get protocol adapter instance
        
        Args:
            protocol_name: Protocol name
            device: Device instance
            
        Returns:
            BaseProtocolAdapter: Protocol adapter instance
        """
        adapter_class = cls._adapters.get(protocol_name.lower())
        if not adapter_class:
            raise ValueError(f"Unknown protocol: {protocol_name}")
            
        return adapter_class(device)
        
    @classmethod
    def list_protocols(cls) -> List[str]:
        """List registered protocols
        
        Returns:
            List[str]: List of protocol names
        """
        return list(cls._adapters.keys())
        
    @classmethod
    def get_protocol_info(cls, protocol_name: str) -> Dict[str, Any]:
        """Get protocol information
        
        Args:
            protocol_name: Protocol name
            
        Returns:
            Dict[str, Any]: Protocol information
        """
        adapter_class = cls._adapters.get(protocol_name.lower())
        if not adapter_class:
            raise ValueError(f"Unknown protocol: {protocol_name}")
            
        # Create temporary instance to get info
        temp_device = Device(
            name="temp",
            device_type=DeviceType.OTHER,
            connection_type=ConnectionType.TCP
        )
        adapter = adapter_class(temp_device)
        
        return {
            "name": adapter.protocol_name,
            "supported_device_types": [dt.value for dt in adapter.supported_device_types],
            "supported_connection_types": [ct.value for ct in adapter.supported_connection_types],
            "capabilities": [cap.value for cap in adapter.capabilities],
        }