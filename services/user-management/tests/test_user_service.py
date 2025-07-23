"""
Test cases for User Service

This module tests the user management service functionality
including user CRUD operations, password management, and role assignment.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from services.user_service import UserService
from db.models import User, UserProfile, Role
from models.schemas import (
    UserRegistrationRequest,
    UserUpdateRequest,
    PaginationParams,
    SortParams,
    FilterParams
)
from core.security import get_password_hash, verify_password


class TestUserService:
    """Test user service functionality"""
    
    @pytest.fixture
    def user_service(self):
        """Create user service instance"""
        return UserService()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.display_name = "Test User"
        user.password_hash = get_password_hash("password123")
        user.is_active = True
        user.is_verified = False
        user.is_superuser = False
        user.roles = []
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        return user
    
    @pytest.fixture
    def mock_profile(self):
        """Create mock user profile"""
        profile = MagicMock(spec=UserProfile)
        profile.user_id = uuid4()
        profile.phone = "+1234567890"
        profile.department = "Engineering"
        profile.job_title = "Developer"
        profile.organization = "Test Corp"
        profile.timezone = "UTC"
        profile.language = "en"
        profile.preferences = {}
        return profile
    
    @pytest.fixture
    def mock_role(self):
        """Create mock role"""
        role = MagicMock(spec=Role)
        role.id = uuid4()
        role.name = "user"
        role.display_name = "User"
        return role
    
    @pytest.fixture
    def user_registration_data(self):
        """Create user registration request data"""
        return UserRegistrationRequest(
            email="newuser@example.com",
            username="newuser",
            password="securepassword123",
            first_name="New",
            last_name="User",
            phone="+1234567890",
            department="Sales",
            job_title="Manager",
            organization="Test Corp",
            timezone="America/New_York",
            language="en"
        )
    
    @pytest.fixture
    def user_update_data(self):
        """Create user update request data"""
        return UserUpdateRequest(
            first_name="Updated",
            last_name="Name",
            display_name="Updated Name",
            phone="+9876543210",
            department="Marketing",
            job_title="Director",
            location="New York",
            bio="Updated bio",
            website="https://example.com",
            preferences={"theme": "dark"}
        )
    
    # User Retrieval Tests
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service, mock_db, mock_user):
        """Test getting user by ID successfully"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await user_service.get_user_by_id(mock_db, mock_user.id)
        
        # Verify
        assert result == mock_user
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service, mock_db):
        """Test getting non-existent user by ID"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await user_service.get_user_by_id(mock_db, uuid4())
        
        # Verify
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service, mock_db, mock_user):
        """Test getting user by email successfully"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await user_service.get_user_by_email(mock_db, "test@example.com")
        
        # Verify
        assert result == mock_user
        assert result.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, user_service, mock_db, mock_user):
        """Test getting user by username successfully"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await user_service.get_user_by_username(mock_db, "testuser")
        
        # Verify
        assert result == mock_user
        assert result.username == "testuser"
    
    # User List Tests
    
    @pytest.mark.asyncio
    async def test_get_users_with_pagination(self, user_service, mock_db, mock_user):
        """Test getting paginated list of users"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_user]
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        pagination = PaginationParams(page=1, limit=10)
        sort = SortParams(sort="email", order="asc")
        filters = FilterParams(is_active=True)
        
        # Test
        users, count = await user_service.get_users(mock_db, pagination, sort, filters)
        
        # Verify
        assert len(users) == 1
        assert count == 1
        assert users[0] == mock_user
    
    @pytest.mark.asyncio
    async def test_get_users_with_filters(self, user_service, mock_db, mock_user):
        """Test getting users with various filters"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_user]
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        pagination = PaginationParams(page=1, limit=10)
        sort = SortParams(sort="created_at", order="desc")
        filters = FilterParams(
            is_active=True,
            is_verified=False,
            department="Engineering",
            organization="Test Corp",
            created_after=datetime(2024, 1, 1),
            created_before=datetime(2024, 12, 31)
        )
        
        # Test
        users, count = await user_service.get_users(mock_db, pagination, sort, filters)
        
        # Verify
        assert len(users) == 1
        assert count == 1
    
    # User Creation Tests
    
    @pytest.mark.asyncio
    async def test_create_user_success(
        self, user_service, mock_db, user_registration_data, mock_role
    ):
        """Test successful user creation"""
        # Setup
        user_service.get_default_role = AsyncMock(return_value=mock_role)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await user_service.create_user(
            mock_db,
            user_registration_data,
            is_superuser=False
        )
        
        # Verify
        assert result.email == user_registration_data.email
        assert result.username == user_registration_data.username
        assert result.first_name == user_registration_data.first_name
        assert result.is_active is True
        assert result.is_verified is False
        assert result.is_superuser is False
        assert mock_db.add.call_count == 2  # User and profile
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_superuser(
        self, user_service, mock_db, user_registration_data, mock_role
    ):
        """Test creating a superuser"""
        # Setup
        user_service.get_default_role = AsyncMock(return_value=mock_role)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await user_service.create_user(
            mock_db,
            user_registration_data,
            is_superuser=True
        )
        
        # Verify
        assert result.is_superuser is True
    
    @pytest.mark.asyncio
    async def test_create_user_database_error(
        self, user_service, mock_db, user_registration_data
    ):
        """Test user creation with database error"""
        # Setup
        mock_db.add = MagicMock()
        mock_db.commit.side_effect = IntegrityError("Duplicate entry", None, None)
        mock_db.rollback = AsyncMock()
        
        # Test
        with pytest.raises(IntegrityError):
            await user_service.create_user(mock_db, user_registration_data)
        
        # Verify
        mock_db.rollback.assert_called_once()
    
    # User Update Tests
    
    @pytest.mark.asyncio
    async def test_update_user_success(
        self, user_service, mock_db, mock_user, mock_profile, user_update_data
    ):
        """Test successful user update"""
        # Setup
        mock_user.profile = mock_profile
        mock_db.refresh = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Test
        result = await user_service.update_user(
            mock_db,
            mock_user,
            user_update_data
        )
        
        # Verify
        assert result.first_name == user_update_data.first_name
        assert result.last_name == user_update_data.last_name
        assert result.display_name == user_update_data.display_name
        assert mock_profile.phone == user_update_data.phone
        assert mock_profile.department == user_update_data.department
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_partial_update(
        self, user_service, mock_db, mock_user, mock_profile
    ):
        """Test partial user update"""
        # Setup
        mock_user.profile = mock_profile
        mock_db.refresh = AsyncMock()
        mock_db.commit = AsyncMock()
        
        partial_update = UserUpdateRequest(
            first_name="PartialUpdate",
            phone="+5555555555"
        )
        
        # Test
        result = await user_service.update_user(
            mock_db,
            mock_user,
            partial_update
        )
        
        # Verify
        assert result.first_name == "PartialUpdate"
        assert mock_profile.phone == "+5555555555"
        # Other fields should remain unchanged
        assert result.last_name == "User"
    
    # User Deletion Tests
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_db, mock_user):
        """Test successful user deletion (soft delete)"""
        # Setup
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        
        # Test
        result = await user_service.delete_user(mock_db, mock_user.id)
        
        # Verify
        assert result is True
        assert mock_user.is_active is False
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, user_service, mock_db):
        """Test deleting non-existent user"""
        # Setup
        user_service.get_user_by_id = AsyncMock(return_value=None)
        
        # Test
        result = await user_service.delete_user(mock_db, uuid4())
        
        # Verify
        assert result is False
    
    # User Activation Tests
    
    @pytest.mark.asyncio
    async def test_activate_user_success(self, user_service, mock_db, mock_user):
        """Test successful user activation"""
        # Setup
        mock_user.is_active = False
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        
        # Test
        result = await user_service.activate_user(mock_db, mock_user.id)
        
        # Verify
        assert result is True
        assert mock_user.is_active is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_user_email_success(self, user_service, mock_db, mock_user):
        """Test successful email verification"""
        # Setup
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        
        # Test
        result = await user_service.verify_user_email(mock_db, mock_user.id)
        
        # Verify
        assert result is True
        assert mock_user.is_verified is True
        assert mock_user.email_verified_at is not None
        mock_db.commit.assert_called_once()
    
    # Password Management Tests
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, mock_db, mock_user):
        """Test successful password change"""
        # Setup
        current_password = "password123"
        new_password = "newpassword456"
        mock_user.password_hash = get_password_hash(current_password)
        mock_db.commit = AsyncMock()
        
        # Test
        result = await user_service.change_password(
            mock_db,
            mock_user,
            current_password,
            new_password
        )
        
        # Verify
        assert result is True
        assert verify_password(new_password, mock_user.password_hash)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, user_service, mock_db, mock_user):
        """Test password change with wrong current password"""
        # Setup
        mock_user.password_hash = get_password_hash("password123")
        
        # Test
        result = await user_service.change_password(
            mock_db,
            mock_user,
            "wrongpassword",
            "newpassword456"
        )
        
        # Verify
        assert result is False
        mock_db.commit.assert_not_called()
    
    # Role Assignment Tests
    
    @pytest.mark.asyncio
    async def test_assign_role_success(self, user_service, mock_db, mock_user, mock_role):
        """Test successful role assignment"""
        # Setup
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_role
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Test
        result = await user_service.assign_role(mock_db, mock_user.id, "user")
        
        # Verify
        assert result is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self, user_service, mock_db):
        """Test role assignment with non-existent user"""
        # Setup
        user_service.get_user_by_id = AsyncMock(return_value=None)
        
        # Test
        result = await user_service.assign_role(mock_db, uuid4(), "user")
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_assign_role_role_not_found(self, user_service, mock_db, mock_user):
        """Test role assignment with non-existent role"""
        # Setup
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await user_service.assign_role(mock_db, mock_user.id, "nonexistent")
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_assign_role_already_assigned(
        self, user_service, mock_db, mock_user, mock_role
    ):
        """Test role assignment when already assigned"""
        # Setup
        mock_user.roles = [mock_role]
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_role
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await user_service.assign_role(mock_db, mock_user.id, "user")
        
        # Verify
        assert result is True
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_remove_role_success(self, user_service, mock_db, mock_user, mock_role):
        """Test successful role removal"""
        # Setup
        mock_user.roles = [mock_role]
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_role
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Test
        result = await user_service.remove_role(mock_db, mock_user.id, "user")
        
        # Verify
        assert result is True
        assert mock_role not in mock_user.roles
        mock_db.commit.assert_called_once()
    
    # User Search Tests
    
    @pytest.mark.asyncio
    async def test_search_users_success(self, user_service, mock_db, mock_user):
        """Test successful user search"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_user]
        mock_db.execute.return_value = mock_result
        
        # Test
        results = await user_service.search_users(mock_db, "test", limit=5)
        
        # Verify
        assert len(results) == 1
        assert results[0] == mock_user
    
    @pytest.mark.asyncio
    async def test_search_users_empty_results(self, user_service, mock_db):
        """Test user search with no results"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Test
        results = await user_service.search_users(mock_db, "nonexistent")
        
        # Verify
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_users_error_handling(self, user_service, mock_db):
        """Test user search error handling"""
        # Setup
        mock_db.execute.side_effect = Exception("Database error")
        
        # Test
        results = await user_service.search_users(mock_db, "test")
        
        # Verify
        assert results == []
    
    # Default Role Tests
    
    @pytest.mark.asyncio
    async def test_get_default_role_success(self, user_service, mock_db, mock_role):
        """Test getting default role"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_role
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await user_service.get_default_role(mock_db)
        
        # Verify
        assert result == mock_role
        assert result.name == "user"
    
    @pytest.mark.asyncio
    async def test_get_default_role_not_found(self, user_service, mock_db):
        """Test getting default role when not found"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await user_service.get_default_role(mock_db)
        
        # Verify
        assert result is None