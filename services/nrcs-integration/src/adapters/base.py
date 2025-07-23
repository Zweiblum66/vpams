"""Base NRCS adapter interface"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncIterator
from datetime import datetime
from uuid import UUID

from ..db.models import NRCSSystem


class NRCSAdapter(ABC):
    """Abstract base class for NRCS adapters"""
    
    def __init__(self, system: NRCSSystem):
        self.system = system
        self.is_connected = False
        self._connection = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to NRCS system"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from NRCS system"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection and return status"""
        pass
    
    @abstractmethod
    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        pass
    
    # Story operations
    @abstractmethod
    async def get_stories(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get stories from NRCS system"""
        pass
    
    @abstractmethod
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Get single story by ID"""
        pass
    
    @abstractmethod
    async def create_story(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new story in NRCS system"""
        pass
    
    @abstractmethod
    async def update_story(self, story_id: str, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing story"""
        pass
    
    @abstractmethod
    async def delete_story(self, story_id: str) -> bool:
        """Delete story from NRCS system"""
        pass
    
    # Rundown operations
    @abstractmethod
    async def get_rundowns(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get rundowns from NRCS system"""
        pass
    
    @abstractmethod
    async def get_rundown(self, rundown_id: str) -> Optional[Dict[str, Any]]:
        """Get single rundown by ID"""
        pass
    
    @abstractmethod
    async def create_rundown(self, rundown_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new rundown"""
        pass
    
    @abstractmethod
    async def update_rundown(self, rundown_id: str, rundown_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing rundown"""
        pass
    
    @abstractmethod
    async def delete_rundown(self, rundown_id: str) -> bool:
        """Delete rundown"""
        pass
    
    @abstractmethod
    async def get_rundown_items(self, rundown_id: str) -> List[Dict[str, Any]]:
        """Get items for a rundown"""
        pass
    
    # User operations
    @abstractmethod
    async def get_users(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get users from NRCS system"""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get single user by ID"""
        pass
    
    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        pass
    
    # Assignment operations
    @abstractmethod
    async def get_assignments(
        self, 
        user_id: Optional[str] = None,
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get assignments"""
        pass
    
    @abstractmethod
    async def create_assignment(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new assignment"""
        pass
    
    @abstractmethod
    async def update_assignment(self, assignment_id: str, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update assignment"""
        pass
    
    # Search operations
    @abstractmethod
    async def search_content(
        self, 
        query: str, 
        content_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search content in NRCS system"""
        pass
    
    # Archive operations
    @abstractmethod
    async def search_archive(
        self, 
        query: str, 
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search archived content"""
        pass
    
    # Wire service operations
    @abstractmethod
    async def get_wire_feeds(self) -> List[Dict[str, Any]]:
        """Get available wire service feeds"""
        pass
    
    @abstractmethod
    async def get_wire_stories(
        self, 
        feed_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get stories from wire feed"""
        pass
    
    # Real-time operations (optional)
    async def subscribe_to_updates(self, callback) -> bool:
        """Subscribe to real-time updates"""
        return False
    
    async def unsubscribe_from_updates(self) -> bool:
        """Unsubscribe from real-time updates"""
        return False
    
    # Health monitoring
    async def get_health_status(self) -> Dict[str, Any]:
        """Get adapter health status"""
        return {
            "adapter": self.__class__.__name__,
            "system": self.system.name,
            "connected": self.is_connected,
            "last_check": datetime.utcnow().isoformat()
        }
    
    # Utility methods
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration"""
        return self.system.config
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "host": self.system.host,
            "port": self.system.port,
            "api_url": self.system.api_url,
            "websocket_url": self.system.websocket_url
        }


class GenericNRCSAdapter(NRCSAdapter):
    """Generic NRCS adapter with basic functionality"""
    
    async def connect(self) -> bool:
        """Basic connection implementation"""
        self.is_connected = True
        return True
    
    async def disconnect(self) -> bool:
        """Basic disconnection implementation"""
        self.is_connected = False
        return True
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection"""
        return {
            "connected": self.is_connected,
            "system": self.system.name,
            "status": "ok" if self.is_connected else "disconnected"
        }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get basic system info"""
        return {
            "name": self.system.name,
            "type": self.system.system_type,
            "vendor": self.system.vendor,
            "version": self.system.version
        }
    
    # Basic implementations that return empty data
    async def get_stories(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        return []
    
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        return None
    
    async def create_story(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": "generic_story_1", "status": "created"}
    
    async def update_story(self, story_id: str, story_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": story_id, "status": "updated"}
    
    async def delete_story(self, story_id: str) -> bool:
        return True
    
    async def get_rundowns(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        return []
    
    async def get_rundown(self, rundown_id: str) -> Optional[Dict[str, Any]]:
        return None
    
    async def create_rundown(self, rundown_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": "generic_rundown_1", "status": "created"}
    
    async def update_rundown(self, rundown_id: str, rundown_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": rundown_id, "status": "updated"}
    
    async def delete_rundown(self, rundown_id: str) -> bool:
        return True
    
    async def get_rundown_items(self, rundown_id: str) -> List[Dict[str, Any]]:
        return []
    
    async def get_users(
        self, 
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        return []
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        return None
    
    async def get_assignments(
        self, 
        user_id: Optional[str] = None,
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        return []
    
    async def create_assignment(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": "generic_assignment_1", "status": "created"}
    
    async def update_assignment(self, assignment_id: str, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": assignment_id, "status": "updated"}
    
    async def search_content(
        self, 
        query: str, 
        content_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        return {"results": [], "total": 0}
    
    async def search_archive(
        self, 
        query: str, 
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        return {"results": [], "total": 0}
    
    async def get_wire_feeds(self) -> List[Dict[str, Any]]:
        return []
    
    async def get_wire_stories(
        self, 
        feed_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return []