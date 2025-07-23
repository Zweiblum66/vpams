"""
Multi-Factor Authentication (MFA) Service

This module handles MFA operations including TOTP setup, verification,
backup codes generation, and SMS-based 2FA.
"""

import io
import base64
import secrets
import string
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from qrcode.image.pil import PilImage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from passlib.context import CryptContext

from ..core.config import get_settings
from ..core.exceptions import (
    InvalidCredentialsError,
    MFARequiredError,
    MFANotEnabledError,
    InvalidMFACodeError,
    MFAAlreadyEnabledError
)
from ..db.models import User
from ..models.schemas import UserResponse

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MFAService:
    """Service for handling Multi-Factor Authentication operations"""
    
    def __init__(self):
        self.issuer_name = settings.APP_NAME or "MAMS"
        self.totp_digits = 6
        self.totp_interval = 30
        self.backup_codes_count = 10
        self.backup_code_length = 8
        
    async def setup_totp(
        self, 
        db: AsyncSession, 
        user: User
    ) -> Tuple[str, str, List[str]]:
        """
        Setup TOTP for a user
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            Tuple of (secret, qr_code_data_url, backup_codes)
            
        Raises:
            MFAAlreadyEnabledError: If MFA is already enabled
        """
        if user.mfa_enabled:
            raise MFAAlreadyEnabledError("MFA is already enabled for this user")
        
        # Generate secret
        secret = pyotp.random_base32()
        
        # Generate backup codes
        backup_codes = self._generate_backup_codes()
        
        # Create provisioning URI
        totp = pyotp.TOTP(secret, interval=self.totp_interval)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=self.issuer_name
        )
        
        # Generate QR code
        qr_code_data_url = self._generate_qr_code(provisioning_uri)
        
        # Store secret and backup codes (hashed) temporarily
        # They will be permanently saved after verification
        user.mfa_secret = secret
        user.backup_codes = [
            pwd_context.hash(code) for code in backup_codes
        ]
        
        await db.commit()
        
        return secret, qr_code_data_url, backup_codes
    
    async def verify_totp_setup(
        self,
        db: AsyncSession,
        user: User,
        code: str
    ) -> bool:
        """
        Verify TOTP setup with user-provided code
        
        Args:
            db: Database session
            user: User object
            code: TOTP code to verify
            
        Returns:
            True if verification successful
            
        Raises:
            MFANotEnabledError: If MFA setup not initiated
            InvalidMFACodeError: If code is invalid
        """
        if not user.mfa_secret:
            raise MFANotEnabledError("MFA setup not initiated")
        
        if user.mfa_enabled:
            raise MFAAlreadyEnabledError("MFA is already enabled")
        
        # Verify the code
        totp = pyotp.TOTP(user.mfa_secret, interval=self.totp_interval)
        if totp.verify(code, valid_window=1):
            # Enable MFA for the user
            user.mfa_enabled = True
            await db.commit()
            return True
        else:
            raise InvalidMFACodeError("Invalid verification code")
    
    async def verify_totp(
        self,
        user: User,
        code: str
    ) -> bool:
        """
        Verify TOTP code for authentication
        
        Args:
            user: User object
            code: TOTP code to verify
            
        Returns:
            True if code is valid
            
        Raises:
            MFANotEnabledError: If MFA is not enabled
            InvalidMFACodeError: If code is invalid
        """
        if not user.mfa_enabled or not user.mfa_secret:
            raise MFANotEnabledError("MFA is not enabled for this user")
        
        totp = pyotp.TOTP(user.mfa_secret, interval=self.totp_interval)
        if totp.verify(code, valid_window=1):
            return True
        else:
            raise InvalidMFACodeError("Invalid MFA code")
    
    async def verify_backup_code(
        self,
        db: AsyncSession,
        user: User,
        code: str
    ) -> bool:
        """
        Verify and consume a backup code
        
        Args:
            db: Database session
            user: User object
            code: Backup code to verify
            
        Returns:
            True if code is valid and consumed
            
        Raises:
            MFANotEnabledError: If MFA is not enabled
            InvalidMFACodeError: If code is invalid
        """
        if not user.mfa_enabled:
            raise MFANotEnabledError("MFA is not enabled for this user")
        
        if not user.backup_codes:
            raise InvalidMFACodeError("No backup codes available")
        
        # Check if the code matches any stored backup code
        for i, hashed_code in enumerate(user.backup_codes):
            if pwd_context.verify(code, hashed_code):
                # Remove the used backup code
                user.backup_codes.pop(i)
                await db.commit()
                return True
        
        raise InvalidMFACodeError("Invalid backup code")
    
    async def regenerate_backup_codes(
        self,
        db: AsyncSession,
        user: User
    ) -> List[str]:
        """
        Generate new backup codes for a user
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            List of new backup codes
            
        Raises:
            MFANotEnabledError: If MFA is not enabled
        """
        if not user.mfa_enabled:
            raise MFANotEnabledError("MFA must be enabled to generate backup codes")
        
        # Generate new backup codes
        backup_codes = self._generate_backup_codes()
        
        # Store hashed versions
        user.backup_codes = [
            pwd_context.hash(code) for code in backup_codes
        ]
        
        await db.commit()
        
        return backup_codes
    
    async def disable_mfa(
        self,
        db: AsyncSession,
        user: User,
        password: str
    ) -> bool:
        """
        Disable MFA for a user
        
        Args:
            db: Database session
            user: User object
            password: User's password for verification
            
        Returns:
            True if MFA disabled successfully
            
        Raises:
            MFANotEnabledError: If MFA is not enabled
            InvalidCredentialsError: If password is incorrect
        """
        if not user.mfa_enabled:
            raise MFANotEnabledError("MFA is not enabled for this user")
        
        # Verify password
        if not pwd_context.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid password")
        
        # Disable MFA
        user.mfa_enabled = False
        user.mfa_secret = None
        user.backup_codes = None
        
        await db.commit()
        
        return True
    
    async def get_mfa_status(self, user: User) -> Dict[str, Any]:
        """
        Get MFA status for a user
        
        Args:
            user: User object
            
        Returns:
            Dictionary with MFA status information
        """
        return {
            "mfa_enabled": user.mfa_enabled,
            "backup_codes_count": len(user.backup_codes) if user.backup_codes else 0,
            "methods": ["totp"] if user.mfa_enabled else []
        }
    
    def _generate_backup_codes(self) -> List[str]:
        """Generate a list of backup codes"""
        codes = []
        alphabet = string.ascii_uppercase + string.digits
        
        for _ in range(self.backup_codes_count):
            code = ''.join(
                secrets.choice(alphabet) 
                for _ in range(self.backup_code_length)
            )
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        
        return codes
    
    def _generate_qr_code(self, provisioning_uri: str) -> str:
        """
        Generate QR code as data URL
        
        Args:
            provisioning_uri: TOTP provisioning URI
            
        Returns:
            Base64 encoded data URL of QR code image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"


class SMSService:
    """Service for handling SMS-based 2FA operations"""
    
    def __init__(self):
        self.code_length = 6
        self.code_expiry_minutes = 10
        self.max_attempts = 3
        # In production, this would integrate with SMS providers like Twilio
        self._pending_codes: Dict[str, Dict[str, Any]] = {}
    
    async def send_sms_code(
        self,
        db: AsyncSession,
        user: User,
        phone_number: str
    ) -> bool:
        """
        Send SMS verification code
        
        Args:
            db: Database session
            user: User object
            phone_number: Phone number to send code to
            
        Returns:
            True if SMS sent successfully
        """
        # Generate code
        code = ''.join(
            secrets.choice(string.digits) 
            for _ in range(self.code_length)
        )
        
        # Store code temporarily (in production, use Redis or database)
        self._pending_codes[user.id] = {
            "code": code,
            "phone": phone_number,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=self.code_expiry_minutes),
            "attempts": 0
        }
        
        # In production, integrate with SMS provider
        # For now, we'll just log it (in real implementation, remove this)
        print(f"SMS Code for {phone_number}: {code}")
        
        return True
    
    async def verify_sms_code(
        self,
        user: User,
        code: str
    ) -> bool:
        """
        Verify SMS code
        
        Args:
            user: User object
            code: SMS code to verify
            
        Returns:
            True if code is valid
            
        Raises:
            InvalidMFACodeError: If code is invalid or expired
        """
        if user.id not in self._pending_codes:
            raise InvalidMFACodeError("No pending SMS verification")
        
        pending = self._pending_codes[user.id]
        
        # Check expiry
        if datetime.now(timezone.utc) > pending["expires_at"]:
            del self._pending_codes[user.id]
            raise InvalidMFACodeError("SMS code has expired")
        
        # Check attempts
        pending["attempts"] += 1
        if pending["attempts"] > self.max_attempts:
            del self._pending_codes[user.id]
            raise InvalidMFACodeError("Too many attempts")
        
        # Verify code
        if pending["code"] == code:
            del self._pending_codes[user.id]
            return True
        else:
            if pending["attempts"] >= self.max_attempts:
                del self._pending_codes[user.id]
            raise InvalidMFACodeError("Invalid SMS code")


# Create service instances
mfa_service = MFAService()
sms_service = SMSService()