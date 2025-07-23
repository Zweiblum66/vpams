"""Main tests for User Management service."""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestHealthCheck:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "user-management"


class TestUserRegistration:
    """Test user registration functionality."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: dict):
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": test_user["email"],
                "username": "anotheruser",
                "password": "password123",
                "full_name": "Another User"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email."""
        response = await client.post(
            "/api/v1/users/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "password": "password123",
                "full_name": "Test User"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthentication:
    """Test authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: dict):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "wronguser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, auth_headers: dict):
        """Test token refresh."""
        response = await client.post(
            "/api/v1/auth/refresh",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data


class TestUserProfile:
    """Test user profile endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict, test_user: dict):
        """Test getting current user profile."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["username"] == test_user["username"]
    
    @pytest.mark.asyncio
    async def test_update_user_profile(self, client: AsyncClient, auth_headers: dict):
        """Test updating user profile."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "full_name": "Updated Name",
                "phone": "+1234567890"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["phone"] == "+1234567890"
    
    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers: dict, test_user: dict):
        """Test changing password."""
        response = await client.post(
            "/api/v1/users/me/change-password",
            headers=auth_headers,
            json={
                "current_password": test_user["password"],
                "new_password": "newsecurepassword123"
            }
        )
        assert response.status_code == status.HTTP_200_OK


class TestUserManagement:
    """Test user management endpoints (admin only)."""
    
    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, admin_auth_headers: dict):
        """Test listing all users (admin only)."""
        response = await client.get("/api/v1/users", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "meta" in data
    
    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self, client: AsyncClient, auth_headers: dict):
        """Test listing users without admin privileges."""
        response = await client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self, client: AsyncClient, admin_auth_headers: dict, test_user: dict):
        """Test deactivating a user (admin only)."""
        response = await client.patch(
            f"/api/v1/users/{test_user['id']}/deactivate",
            headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False


class TestRoleManagement:
    """Test role and permission management."""
    
    @pytest.mark.asyncio
    async def test_create_role(self, client: AsyncClient, admin_auth_headers: dict):
        """Test creating a new role."""
        response = await client.post(
            "/api/v1/roles",
            headers=admin_auth_headers,
            json={
                "name": "editor",
                "description": "Can edit assets",
                "permissions": ["asset:read", "asset:write", "asset:update"]
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "editor"
        assert len(data["permissions"]) == 3
    
    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, client: AsyncClient, admin_auth_headers: dict, test_user: dict):
        """Test assigning role to user."""
        # First create a role
        role_response = await client.post(
            "/api/v1/roles",
            headers=admin_auth_headers,
            json={
                "name": "viewer",
                "description": "Can view assets",
                "permissions": ["asset:read"]
            }
        )
        role_id = role_response.json()["id"]
        
        # Assign role to user
        response = await client.post(
            f"/api/v1/users/{test_user['id']}/roles",
            headers=admin_auth_headers,
            json={"role_id": role_id}
        )
        assert response.status_code == status.HTTP_200_OK