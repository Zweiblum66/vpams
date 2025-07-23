"""
Users resource implementation
"""

from typing import Optional, Dict, Any, List
from ..resources.base import BaseResource
from ..models import User, UserCreate, UserUpdate


class UsersResource(BaseResource[User]):
    """Users API resource"""
    
    def __init__(self, client):
        super().__init__(client)
        self.resource_name = "users"
        self.model_class = User
    
    def get_current(self) -> User:
        """Get current user profile
        
        Returns:
            Current user object
        """
        response = self._make_request(
            "GET",
            self._get_path("me")
        )
        
        return self._parse_response(response)
    
    def update_current(self, **updates) -> User:
        """Update current user profile
        
        Args:
            **updates: Fields to update
        
        Returns:
            Updated user object
        """
        response = self._make_request(
            "PATCH",
            self._get_path("me"),
            json=updates
        )
        
        return self._parse_response(response)
    
    def change_password(
        self,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password
        
        Args:
            current_password: Current password
            new_password: New password
        
        Returns:
            True if successful
        """
        data = {
            "current_password": current_password,
            "new_password": new_password
        }
        
        self._make_request(
            "POST",
            self._get_path("me", "change-password"),
            json=data
        )
        return True
    
    def get_permissions(self, user_id: Optional[str] = None) -> List[str]:
        """Get user permissions
        
        Args:
            user_id: Optional user ID (defaults to current user)
        
        Returns:
            List of permissions
        """
        path = "me/permissions" if not user_id else f"{user_id}/permissions"
        
        response = self._make_request(
            "GET",
            self._get_path(path)
        )
        
        return response.get("data", [])
    
    def get_roles(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user roles
        
        Args:
            user_id: Optional user ID (defaults to current user)
        
        Returns:
            List of roles
        """
        path = "me/roles" if not user_id else f"{user_id}/roles"
        
        response = self._make_request(
            "GET",
            self._get_path(path)
        )
        
        return response.get("data", [])
    
    def assign_role(
        self,
        user_id: str,
        role_id: str,
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assign role to user
        
        Args:
            user_id: User ID
            role_id: Role ID
            scope: Optional scope (project, organization)
        
        Returns:
            Role assignment
        """
        data = {"role_id": role_id}
        
        if scope:
            data["scope"] = scope
        
        response = self._make_request(
            "POST",
            self._get_path(user_id, "roles"),
            json=data
        )
        
        return response.get("data", {})
    
    def remove_role(
        self,
        user_id: str,
        role_id: str
    ) -> bool:
        """Remove role from user
        
        Args:
            user_id: User ID
            role_id: Role ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "DELETE",
            self._get_path(user_id, "roles", role_id)
        )
        return True
    
    def get_projects(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user projects
        
        Args:
            user_id: Optional user ID (defaults to current user)
        
        Returns:
            List of projects
        """
        path = "me/projects" if not user_id else f"{user_id}/projects"
        
        response = self._make_request(
            "GET",
            self._get_path(path)
        )
        
        return response.get("data", [])
    
    def get_activity(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user activity
        
        Args:
            user_id: Optional user ID (defaults to current user)
            limit: Results limit
            activity_type: Optional activity type filter
        
        Returns:
            List of activities
        """
        path = "me/activity" if not user_id else f"{user_id}/activity"
        
        params = {"limit": limit}
        if activity_type:
            params["type"] = activity_type
        
        response = self._make_request(
            "GET",
            self._get_path(path),
            params=params
        )
        
        return response.get("data", [])
    
    def get_preferences(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get user preferences
        
        Args:
            user_id: Optional user ID (defaults to current user)
        
        Returns:
            User preferences
        """
        path = "me/preferences" if not user_id else f"{user_id}/preferences"
        
        response = self._make_request(
            "GET",
            self._get_path(path)
        )
        
        return response.get("data", {})
    
    def update_preferences(
        self,
        preferences: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user preferences
        
        Args:
            preferences: Preferences to update
            user_id: Optional user ID (defaults to current user)
        
        Returns:
            Updated preferences
        """
        path = "me/preferences" if not user_id else f"{user_id}/preferences"
        
        response = self._make_request(
            "PATCH",
            self._get_path(path),
            json=preferences
        )
        
        return response.get("data", {})
    
    def get_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user sessions
        
        Args:
            user_id: Optional user ID (defaults to current user)
        
        Returns:
            List of active sessions
        """
        path = "me/sessions" if not user_id else f"{user_id}/sessions"
        
        response = self._make_request(
            "GET",
            self._get_path(path)
        )
        
        return response.get("data", [])
    
    def revoke_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Revoke user session
        
        Args:
            session_id: Session ID
            user_id: Optional user ID (defaults to current user)
        
        Returns:
            True if successful
        """
        path = f"me/sessions/{session_id}" if not user_id else f"{user_id}/sessions/{session_id}"
        
        self._make_request(
            "DELETE",
            self._get_path(path)
        )
        return True
    
    def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[User]:
        """Search users
        
        Args:
            query: Search query
            limit: Results limit
            filters: Optional filters
        
        Returns:
            List of matching users
        """
        params = {
            "q": query,
            "limit": limit
        }
        
        if filters:
            params.update(filters)
        
        response = self._make_request(
            "GET",
            self._get_path("search"),
            params=params
        )
        
        return self._parse_list_response(response)