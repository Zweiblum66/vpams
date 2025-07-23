"""
Test cases for Account Lockout Service

This module tests the account lockout functionality including
failed login tracking, account locking, and automatic unlocking.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from services.lockout_service import AccountLockoutService
from db.models import User
from core.config import get_settings


class TestAccountLockoutService:
    """Test account lockout service functionality"""
    
    @pytest.fixture
    def lockout_service(self):
        """Create lockout service instance"""
        return AccountLockoutService()
    
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
        user.failed_login_attempts = 0
        user.account_locked_at = None
        user.updated_at = datetime.now(timezone.utc)
        return user
    
    @pytest.fixture
    def locked_user(self):
        """Create mock locked user"""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "locked@example.com"
        user.failed_login_attempts = 5
        user.account_locked_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        return user
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for lockout configuration"""
        settings = MagicMock()
        settings.max_failed_login_attempts = 5
        settings.account_lockout_duration_minutes = 30
        return settings
    
    # Account Lock Status Tests
    
    @pytest.mark.asyncio
    async def test_is_account_locked_not_locked(self, lockout_service, mock_db, mock_user):
        """Test checking unlocked account"""
        # Test
        result = await lockout_service.is_account_locked(mock_db, mock_user)
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_account_locked_currently_locked(self, lockout_service, mock_db, locked_user):
        """Test checking currently locked account"""
        # Setup - account locked 10 minutes ago
        locked_user.account_locked_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        # Test
        result = await lockout_service.is_account_locked(mock_db, locked_user)
        
        # Verify
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_account_locked_expired_lockout(self, lockout_service, mock_db, locked_user):
        """Test checking account with expired lockout"""
        # Setup - account locked 40 minutes ago (past 30 minute duration)
        locked_user.account_locked_at = datetime.now(timezone.utc) - timedelta(minutes=40)
        lockout_service.unlock_account = AsyncMock(return_value=True)
        
        # Test
        result = await lockout_service.is_account_locked(mock_db, locked_user)
        
        # Verify
        assert result is False
        lockout_service.unlock_account.assert_called_once_with(mock_db, locked_user)
    
    @pytest.mark.asyncio
    async def test_is_account_locked_error_handling(self, lockout_service, mock_db, mock_user):
        """Test error handling in lock status check"""
        # Setup
        mock_user.account_locked_at = MagicMock(side_effect=Exception("Database error"))
        
        # Test
        result = await lockout_service.is_account_locked(mock_db, mock_user)
        
        # Verify - should return False on error
        assert result is False
    
    # Failed Login Attempt Tests
    
    @pytest.mark.asyncio
    async def test_record_failed_attempt_first_attempt(self, lockout_service, mock_db, mock_user):
        """Test recording first failed login attempt"""
        # Setup
        mock_db.commit = AsyncMock()
        
        # Test
        result = await lockout_service.record_failed_attempt(mock_db, mock_user)
        
        # Verify
        assert mock_user.failed_login_attempts == 1
        assert result["locked"] is False
        assert result["attempts"] == 1
        assert result["remaining_attempts"] == 4
        assert "4 attempts remaining" in result["message"]
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_failed_attempt_multiple_attempts(self, lockout_service, mock_db, mock_user):
        """Test recording multiple failed attempts"""
        # Setup
        mock_user.failed_login_attempts = 3
        mock_db.commit = AsyncMock()
        
        # Test
        result = await lockout_service.record_failed_attempt(mock_db, mock_user)
        
        # Verify
        assert mock_user.failed_login_attempts == 4
        assert result["locked"] is False
        assert result["attempts"] == 4
        assert result["remaining_attempts"] == 1
        assert "1 attempts remaining" in result["message"]
    
    @pytest.mark.asyncio
    async def test_record_failed_attempt_triggers_lockout(self, lockout_service, mock_db, mock_user):
        """Test recording attempt that triggers lockout"""
        # Setup
        mock_user.failed_login_attempts = 4  # Next attempt will be 5th
        mock_db.commit = AsyncMock()
        
        # Test
        result = await lockout_service.record_failed_attempt(mock_db, mock_user)
        
        # Verify
        assert mock_user.failed_login_attempts == 5
        assert mock_user.account_locked_at is not None
        assert result["locked"] is True
        assert result["attempts"] == 5
        assert "locked_at" in result
        assert "unlock_at" in result
        assert "Account locked" in result["message"]
        assert "30 minutes" in result["message"]
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_failed_attempt_database_error(self, lockout_service, mock_db, mock_user):
        """Test error handling during failed attempt recording"""
        # Setup
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()
        
        # Test
        with pytest.raises(Exception, match="Database error"):
            await lockout_service.record_failed_attempt(mock_db, mock_user)
        
        # Verify
        mock_db.rollback.assert_called_once()
    
    # Successful Login Tests
    
    @pytest.mark.asyncio
    async def test_record_successful_login_reset_attempts(self, lockout_service, mock_db, mock_user):
        """Test recording successful login resets failed attempts"""
        # Setup
        mock_user.failed_login_attempts = 3
        mock_db.commit = AsyncMock()
        
        # Test
        await lockout_service.record_successful_login(mock_db, mock_user)
        
        # Verify
        assert mock_user.failed_login_attempts == 0
        assert mock_user.account_locked_at is None
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_successful_login_no_failed_attempts(self, lockout_service, mock_db, mock_user):
        """Test recording successful login with no prior failed attempts"""
        # Setup
        mock_user.failed_login_attempts = 0
        mock_db.commit = AsyncMock()
        
        # Test
        await lockout_service.record_successful_login(mock_db, mock_user)
        
        # Verify - should not commit if no changes needed
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_record_successful_login_clears_lockout(self, lockout_service, mock_db, locked_user):
        """Test successful login clears lockout"""
        # Setup
        mock_db.commit = AsyncMock()
        
        # Test
        await lockout_service.record_successful_login(mock_db, locked_user)
        
        # Verify
        assert locked_user.failed_login_attempts == 0
        assert locked_user.account_locked_at is None
        mock_db.commit.assert_called_once()
    
    # Manual Unlock Tests
    
    @pytest.mark.asyncio
    async def test_unlock_account_success(self, lockout_service, mock_db, locked_user):
        """Test manually unlocking account"""
        # Setup
        mock_db.commit = AsyncMock()
        
        # Test
        result = await lockout_service.unlock_account(mock_db, locked_user)
        
        # Verify
        assert result is True
        assert locked_user.failed_login_attempts == 0
        assert locked_user.account_locked_at is None
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unlock_account_database_error(self, lockout_service, mock_db, locked_user):
        """Test error handling during account unlock"""
        # Setup
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()
        
        # Test
        result = await lockout_service.unlock_account(mock_db, locked_user)
        
        # Verify
        assert result is False
        mock_db.rollback.assert_called_once()
    
    # Lockout Information Tests
    
    @pytest.mark.asyncio
    async def test_get_lockout_info_unlocked(self, lockout_service, mock_user):
        """Test getting lockout info for unlocked account"""
        # Setup
        mock_user.failed_login_attempts = 2
        
        # Test
        info = await lockout_service.get_lockout_info(mock_user)
        
        # Verify
        assert info["locked"] is False
        assert info["failed_attempts"] == 2
        assert info["remaining_attempts"] == 3
    
    @pytest.mark.asyncio
    async def test_get_lockout_info_locked(self, lockout_service, locked_user):
        """Test getting lockout info for locked account"""
        # Setup
        locked_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        locked_user.account_locked_at = locked_time
        
        # Test
        info = await lockout_service.get_lockout_info(locked_user)
        
        # Verify
        assert info["locked"] is True
        assert info["failed_attempts"] == 5
        assert "locked_at" in info
        assert "unlock_at" in info
        assert info["remaining_minutes"] == 20  # 30 - 10 minutes
    
    @pytest.mark.asyncio
    async def test_get_lockout_info_error_handling(self, lockout_service, mock_user):
        """Test error handling in get lockout info"""
        # Setup
        mock_user.account_locked_at = MagicMock(side_effect=Exception("Error"))
        
        # Test
        info = await lockout_service.get_lockout_info(mock_user)
        
        # Verify - should return default values
        assert info["locked"] is False
        assert info["failed_attempts"] == 0
        assert info["remaining_attempts"] == 5
    
    # Locked Users Query Tests
    
    @pytest.mark.asyncio
    async def test_get_locked_users_success(self, lockout_service, mock_db, locked_user):
        """Test getting list of locked users"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [locked_user]
        mock_db.execute.return_value = mock_result
        
        # Test
        locked_users = await lockout_service.get_locked_users(mock_db, limit=10)
        
        # Verify
        assert len(locked_users) == 1
        assert locked_users[0] == locked_user
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_locked_users_empty(self, lockout_service, mock_db):
        """Test getting locked users when none exist"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Test
        locked_users = await lockout_service.get_locked_users(mock_db)
        
        # Verify
        assert len(locked_users) == 0
    
    @pytest.mark.asyncio
    async def test_get_locked_users_error_handling(self, lockout_service, mock_db):
        """Test error handling in get locked users"""
        # Setup
        mock_db.execute.side_effect = Exception("Database error")
        
        # Test
        locked_users = await lockout_service.get_locked_users(mock_db)
        
        # Verify
        assert locked_users == []
    
    # Cleanup Tests
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_lockouts_success(self, lockout_service, mock_db):
        """Test cleaning up expired lockouts"""
        # Setup
        expired_user1 = MagicMock(spec=User)
        expired_user1.account_locked_at = datetime.now(timezone.utc) - timedelta(minutes=40)
        expired_user2 = MagicMock(spec=User)
        expired_user2.account_locked_at = datetime.now(timezone.utc) - timedelta(minutes=35)
        
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [expired_user1, expired_user2]
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Test
        count = await lockout_service.cleanup_expired_lockouts(mock_db)
        
        # Verify
        assert count == 2
        assert expired_user1.failed_login_attempts == 0
        assert expired_user1.account_locked_at is None
        assert expired_user2.failed_login_attempts == 0
        assert expired_user2.account_locked_at is None
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_lockouts_none_found(self, lockout_service, mock_db):
        """Test cleanup when no expired lockouts exist"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Test
        count = await lockout_service.cleanup_expired_lockouts(mock_db)
        
        # Verify
        assert count == 0
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_lockouts_error_handling(self, lockout_service, mock_db):
        """Test error handling in cleanup"""
        # Setup
        mock_db.execute.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()
        
        # Test
        count = await lockout_service.cleanup_expired_lockouts(mock_db)
        
        # Verify
        assert count == 0
        mock_db.rollback.assert_called_once()
    
    # Statistics Tests
    
    @pytest.mark.asyncio
    async def test_get_lockout_stats_success(self, lockout_service, mock_db):
        """Test getting lockout statistics"""
        # Setup
        locked_users = [MagicMock(), MagicMock(), MagicMock()]
        failed_users = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        
        mock_locked_result = AsyncMock()
        mock_locked_result.scalars().all.return_value = locked_users
        
        mock_failed_result = AsyncMock()
        mock_failed_result.scalars().all.return_value = failed_users
        
        mock_db.execute.side_effect = [mock_locked_result, mock_failed_result]
        
        # Test
        stats = await lockout_service.get_lockout_stats(mock_db)
        
        # Verify
        assert stats["currently_locked"] == 3
        assert stats["users_with_failed_attempts"] == 5
        assert stats["max_attempts"] == 5
        assert stats["lockout_duration_minutes"] == 30
    
    @pytest.mark.asyncio
    async def test_get_lockout_stats_error_handling(self, lockout_service, mock_db):
        """Test error handling in get lockout stats"""
        # Setup
        mock_db.execute.side_effect = Exception("Database error")
        
        # Test
        stats = await lockout_service.get_lockout_stats(mock_db)
        
        # Verify - should return default values
        assert stats["currently_locked"] == 0
        assert stats["users_with_failed_attempts"] == 0
        assert stats["max_attempts"] == 5
        assert stats["lockout_duration_minutes"] == 30
    
    # Configuration Tests
    
    def test_lockout_service_initialization(self, mock_settings):
        """Test lockout service initialization with custom settings"""
        # Setup
        with patch('services.lockout_service.settings', mock_settings):
            # Test
            service = AccountLockoutService()
        
        # Verify
        assert service.max_attempts == 5
        assert service.lockout_duration == 30