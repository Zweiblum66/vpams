"""
Tests for MFA Service

This module contains tests for the Multi-Factor Authentication service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
import pyotp

from src.services.mfa_service import MFAService, SMSService
from src.core.exceptions import (
    MFANotEnabledError,
    InvalidMFACodeError,
    MFAAlreadyEnabledError,
    InvalidCredentialsError
)
from src.db.models import User


@pytest.fixture
def mfa_service():
    """Create MFA service instance"""
    return MFAService()


@pytest.fixture
def sms_service():
    """Create SMS service instance"""
    return SMSService()


@pytest.fixture
def mock_user():
    """Create mock user"""
    user = Mock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.mfa_enabled = False
    user.mfa_secret = None
    user.backup_codes = None
    user.password_hash = "$2b$12$test_hash"
    return user


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


class TestMFAService:
    """Test cases for MFA Service"""
    
    @pytest.mark.asyncio
    async def test_setup_totp_success(self, mfa_service, mock_user, mock_db):
        """Test successful TOTP setup"""
        secret, qr_code, backup_codes = await mfa_service.setup_totp(mock_db, mock_user)
        
        assert secret is not None
        assert len(secret) == 32  # Base32 encoded secret
        assert qr_code.startswith("data:image/png;base64,")
        assert len(backup_codes) == 10
        assert all(len(code) == 9 and '-' in code for code in backup_codes)  # Format: XXXX-XXXX
        
        assert mock_user.mfa_secret == secret
        assert len(mock_user.backup_codes) == 10
        await mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_totp_already_enabled(self, mfa_service, mock_user, mock_db):
        """Test TOTP setup when MFA is already enabled"""
        mock_user.mfa_enabled = True
        
        with pytest.raises(MFAAlreadyEnabledError):
            await mfa_service.setup_totp(mock_db, mock_user)
    
    @pytest.mark.asyncio
    async def test_verify_totp_setup_success(self, mfa_service, mock_user, mock_db):
        """Test successful TOTP setup verification"""
        # Setup TOTP first
        secret, _, _ = await mfa_service.setup_totp(mock_db, mock_user)
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Verify setup
        result = await mfa_service.verify_totp_setup(mock_db, mock_user, valid_code)
        
        assert result is True
        assert mock_user.mfa_enabled is True
        assert await mock_db.commit.call_count == 2  # Once for setup, once for verify
    
    @pytest.mark.asyncio
    async def test_verify_totp_setup_invalid_code(self, mfa_service, mock_user, mock_db):
        """Test TOTP setup verification with invalid code"""
        # Setup TOTP first
        await mfa_service.setup_totp(mock_db, mock_user)
        
        # Try with invalid code
        with pytest.raises(InvalidMFACodeError):
            await mfa_service.verify_totp_setup(mock_db, mock_user, "000000")
    
    @pytest.mark.asyncio
    async def test_verify_totp_setup_not_initiated(self, mfa_service, mock_user, mock_db):
        """Test TOTP setup verification when setup not initiated"""
        with pytest.raises(MFANotEnabledError):
            await mfa_service.verify_totp_setup(mock_db, mock_user, "123456")
    
    @pytest.mark.asyncio
    async def test_verify_totp_success(self, mfa_service, mock_user):
        """Test successful TOTP verification for login"""
        secret = pyotp.random_base32()
        mock_user.mfa_enabled = True
        mock_user.mfa_secret = secret
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        result = await mfa_service.verify_totp(mock_user, valid_code)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_totp_invalid_code(self, mfa_service, mock_user):
        """Test TOTP verification with invalid code"""
        secret = pyotp.random_base32()
        mock_user.mfa_enabled = True
        mock_user.mfa_secret = secret
        
        with pytest.raises(InvalidMFACodeError):
            await mfa_service.verify_totp(mock_user, "000000")
    
    @pytest.mark.asyncio
    async def test_verify_totp_not_enabled(self, mfa_service, mock_user):
        """Test TOTP verification when MFA not enabled"""
        mock_user.mfa_enabled = False
        
        with pytest.raises(MFANotEnabledError):
            await mfa_service.verify_totp(mock_user, "123456")
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_success(self, mfa_service, mock_user, mock_db):
        """Test successful backup code verification"""
        mock_user.mfa_enabled = True
        
        # Mock backup codes (hashed)
        with patch('src.services.mfa_service.pwd_context') as mock_pwd_context:
            mock_pwd_context.verify.return_value = True
            mock_user.backup_codes = ["hashed_code1", "hashed_code2"]
            
            result = await mfa_service.verify_backup_code(mock_db, mock_user, "ABCD-1234")
            
            assert result is True
            assert len(mock_user.backup_codes) == 1  # One code used
            await mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_invalid(self, mfa_service, mock_user, mock_db):
        """Test backup code verification with invalid code"""
        mock_user.mfa_enabled = True
        
        with patch('src.services.mfa_service.pwd_context') as mock_pwd_context:
            mock_pwd_context.verify.return_value = False
            mock_user.backup_codes = ["hashed_code1", "hashed_code2"]
            
            with pytest.raises(InvalidMFACodeError):
                await mfa_service.verify_backup_code(mock_db, mock_user, "INVALID-CODE")
    
    @pytest.mark.asyncio
    async def test_regenerate_backup_codes(self, mfa_service, mock_user, mock_db):
        """Test regenerating backup codes"""
        mock_user.mfa_enabled = True
        
        new_codes = await mfa_service.regenerate_backup_codes(mock_db, mock_user)
        
        assert len(new_codes) == 10
        assert all(len(code) == 9 and '-' in code for code in new_codes)
        assert len(mock_user.backup_codes) == 10
        await mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_regenerate_backup_codes_mfa_not_enabled(self, mfa_service, mock_user, mock_db):
        """Test regenerating backup codes when MFA not enabled"""
        mock_user.mfa_enabled = False
        
        with pytest.raises(MFANotEnabledError):
            await mfa_service.regenerate_backup_codes(mock_db, mock_user)
    
    @pytest.mark.asyncio
    async def test_disable_mfa_success(self, mfa_service, mock_user, mock_db):
        """Test successful MFA disable"""
        mock_user.mfa_enabled = True
        mock_user.mfa_secret = "test_secret"
        mock_user.backup_codes = ["code1", "code2"]
        
        with patch('src.services.mfa_service.pwd_context') as mock_pwd_context:
            mock_pwd_context.verify.return_value = True
            
            result = await mfa_service.disable_mfa(mock_db, mock_user, "password123")
            
            assert result is True
            assert mock_user.mfa_enabled is False
            assert mock_user.mfa_secret is None
            assert mock_user.backup_codes is None
            await mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disable_mfa_wrong_password(self, mfa_service, mock_user, mock_db):
        """Test MFA disable with wrong password"""
        mock_user.mfa_enabled = True
        
        with patch('src.services.mfa_service.pwd_context') as mock_pwd_context:
            mock_pwd_context.verify.return_value = False
            
            with pytest.raises(InvalidCredentialsError):
                await mfa_service.disable_mfa(mock_db, mock_user, "wrong_password")
    
    @pytest.mark.asyncio
    async def test_get_mfa_status(self, mfa_service, mock_user):
        """Test getting MFA status"""
        # Test with MFA disabled
        status = await mfa_service.get_mfa_status(mock_user)
        assert status["mfa_enabled"] is False
        assert status["backup_codes_count"] == 0
        assert status["methods"] == []
        
        # Test with MFA enabled
        mock_user.mfa_enabled = True
        mock_user.backup_codes = ["code1", "code2", "code3"]
        
        status = await mfa_service.get_mfa_status(mock_user)
        assert status["mfa_enabled"] is True
        assert status["backup_codes_count"] == 3
        assert status["methods"] == ["totp"]


class TestSMSService:
    """Test cases for SMS Service"""
    
    @pytest.mark.asyncio
    async def test_send_sms_code(self, sms_service, mock_user, mock_db):
        """Test sending SMS code"""
        phone_number = "+1234567890"
        
        result = await sms_service.send_sms_code(mock_db, mock_user, phone_number)
        
        assert result is True
        assert mock_user.id in sms_service._pending_codes
        assert len(sms_service._pending_codes[mock_user.id]["code"]) == 6
        assert sms_service._pending_codes[mock_user.id]["phone"] == phone_number
    
    @pytest.mark.asyncio
    async def test_verify_sms_code_success(self, sms_service, mock_user, mock_db):
        """Test successful SMS code verification"""
        # Send code first
        await sms_service.send_sms_code(mock_db, mock_user, "+1234567890")
        code = sms_service._pending_codes[mock_user.id]["code"]
        
        # Verify code
        result = await sms_service.verify_sms_code(mock_user, code)
        
        assert result is True
        assert mock_user.id not in sms_service._pending_codes
    
    @pytest.mark.asyncio
    async def test_verify_sms_code_invalid(self, sms_service, mock_user, mock_db):
        """Test SMS code verification with invalid code"""
        # Send code first
        await sms_service.send_sms_code(mock_db, mock_user, "+1234567890")
        
        # Try invalid code
        with pytest.raises(InvalidMFACodeError):
            await sms_service.verify_sms_code(mock_user, "000000")
    
    @pytest.mark.asyncio
    async def test_verify_sms_code_expired(self, sms_service, mock_user, mock_db):
        """Test SMS code verification with expired code"""
        # Send code first
        await sms_service.send_sms_code(mock_db, mock_user, "+1234567890")
        
        # Expire the code
        sms_service._pending_codes[mock_user.id]["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        with pytest.raises(InvalidMFACodeError) as exc_info:
            await sms_service.verify_sms_code(mock_user, "123456")
        
        assert "expired" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_verify_sms_code_max_attempts(self, sms_service, mock_user, mock_db):
        """Test SMS code verification with max attempts exceeded"""
        # Send code first
        await sms_service.send_sms_code(mock_db, mock_user, "+1234567890")
        
        # Try invalid code multiple times
        for i in range(3):
            try:
                await sms_service.verify_sms_code(mock_user, "000000")
            except InvalidMFACodeError:
                pass
        
        # Should be removed after max attempts
        assert mock_user.id not in sms_service._pending_codes