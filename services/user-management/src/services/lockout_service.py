"""
Account Lockout Service

Service for managing account lockout after failed login attempts.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from db.models import User
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AccountLockoutService:
    """Service for managing account lockout functionality"""
    
    def __init__(self):
        self.max_attempts = settings.max_failed_login_attempts
        self.lockout_duration = settings.account_lockout_duration_minutes
    
    async def is_account_locked(self, db: AsyncSession, user: User) -> bool:
        """
        Check if user account is currently locked
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            True if account is locked, False otherwise
        """
        try:
            # Check if account was locked
            if not user.account_locked_at:
                return False
            
            # Check if lockout period has expired
            lockout_expires_at = user.account_locked_at + timedelta(minutes=self.lockout_duration)
            current_time = datetime.now(timezone.utc)
            
            if current_time >= lockout_expires_at:
                # Lockout period has expired, unlock the account
                await self.unlock_account(db, user)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking account lock status: {e}")
            return False
    
    async def record_failed_attempt(self, db: AsyncSession, user: User) -> Dict[str, Any]:
        """
        Record a failed login attempt and lock account if necessary
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            Dictionary with lockout information
        """
        try:
            # Increment failed attempts
            user.failed_login_attempts += 1
            user.updated_at = datetime.now(timezone.utc)
            
            # Check if account should be locked
            if user.failed_login_attempts >= self.max_attempts:
                user.account_locked_at = datetime.now(timezone.utc)
                await db.commit()
                
                logger.warning(f"Account locked due to failed attempts: {user.email}")
                
                return {
                    "locked": True,
                    "attempts": user.failed_login_attempts,
                    "locked_at": user.account_locked_at,
                    "unlock_at": user.account_locked_at + timedelta(minutes=self.lockout_duration),
                    "message": f"Account locked due to {self.max_attempts} failed login attempts. "
                              f"Try again in {self.lockout_duration} minutes."
                }
            else:
                await db.commit()
                
                remaining_attempts = self.max_attempts - user.failed_login_attempts
                
                return {
                    "locked": False,
                    "attempts": user.failed_login_attempts,
                    "remaining_attempts": remaining_attempts,
                    "message": f"Invalid credentials. {remaining_attempts} attempts remaining."
                }
                
        except Exception as e:
            logger.error(f"Error recording failed login attempt: {e}")
            await db.rollback()
            raise
    
    async def record_successful_login(self, db: AsyncSession, user: User) -> None:
        """
        Record successful login and reset failed attempts
        
        Args:
            db: Database session
            user: User object
        """
        try:
            # Reset failed attempts on successful login
            if user.failed_login_attempts > 0:
                user.failed_login_attempts = 0
                user.account_locked_at = None
                user.updated_at = datetime.now(timezone.utc)
                await db.commit()
                
                logger.info(f"Reset failed login attempts for user: {user.email}")
                
        except Exception as e:
            logger.error(f"Error recording successful login: {e}")
            await db.rollback()
            raise
    
    async def unlock_account(self, db: AsyncSession, user: User) -> bool:
        """
        Manually unlock a user account
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            True if account was unlocked, False otherwise
        """
        try:
            user.failed_login_attempts = 0
            user.account_locked_at = None
            user.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Account manually unlocked: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error unlocking account: {e}")
            await db.rollback()
            return False
    
    async def get_lockout_info(self, user: User) -> Dict[str, Any]:
        """
        Get account lockout information
        
        Args:
            user: User object
            
        Returns:
            Dictionary with lockout information
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            if not user.account_locked_at:
                return {
                    "locked": False,
                    "failed_attempts": user.failed_login_attempts,
                    "remaining_attempts": self.max_attempts - user.failed_login_attempts
                }
            
            unlock_at = user.account_locked_at + timedelta(minutes=self.lockout_duration)
            remaining_time = unlock_at - current_time
            
            return {
                "locked": True,
                "failed_attempts": user.failed_login_attempts,
                "locked_at": user.account_locked_at.isoformat(),
                "unlock_at": unlock_at.isoformat(),
                "remaining_minutes": max(0, int(remaining_time.total_seconds() / 60))
            }
            
        except Exception as e:
            logger.error(f"Error getting lockout info: {e}")
            return {
                "locked": False,
                "failed_attempts": 0,
                "remaining_attempts": self.max_attempts
            }
    
    async def get_locked_users(self, db: AsyncSession, limit: int = 100) -> list[User]:
        """
        Get list of currently locked users
        
        Args:
            db: Database session
            limit: Maximum number of users to return
            
        Returns:
            List of locked users
        """
        try:
            current_time = datetime.now(timezone.utc)
            lockout_threshold = current_time - timedelta(minutes=self.lockout_duration)
            
            result = await db.execute(
                select(User)
                .where(
                    User.account_locked_at.is_not(None),
                    User.account_locked_at > lockout_threshold
                )
                .limit(limit)
            )
            
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting locked users: {e}")
            return []
    
    async def cleanup_expired_lockouts(self, db: AsyncSession) -> int:
        """
        Clean up expired account lockouts
        
        Args:
            db: Database session
            
        Returns:
            Number of accounts unlocked
        """
        try:
            current_time = datetime.now(timezone.utc)
            lockout_threshold = current_time - timedelta(minutes=self.lockout_duration)
            
            # Get users with expired lockouts
            result = await db.execute(
                select(User)
                .where(
                    User.account_locked_at.is_not(None),
                    User.account_locked_at <= lockout_threshold
                )
            )
            
            users_to_unlock = result.scalars().all()
            
            # Unlock expired accounts
            for user in users_to_unlock:
                user.failed_login_attempts = 0
                user.account_locked_at = None
                user.updated_at = current_time
            
            await db.commit()
            
            count = len(users_to_unlock)
            if count > 0:
                logger.info(f"Unlocked {count} expired account lockouts")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired lockouts: {e}")
            await db.rollback()
            return 0
    
    async def get_lockout_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get lockout statistics
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with lockout statistics
        """
        try:
            current_time = datetime.now(timezone.utc)
            lockout_threshold = current_time - timedelta(minutes=self.lockout_duration)
            
            # Count currently locked users
            locked_result = await db.execute(
                select(User)
                .where(
                    User.account_locked_at.is_not(None),
                    User.account_locked_at > lockout_threshold
                )
            )
            locked_count = len(locked_result.scalars().all())
            
            # Count users with failed attempts
            failed_result = await db.execute(
                select(User)
                .where(User.failed_login_attempts > 0)
            )
            failed_count = len(failed_result.scalars().all())
            
            return {
                "currently_locked": locked_count,
                "users_with_failed_attempts": failed_count,
                "max_attempts": self.max_attempts,
                "lockout_duration_minutes": self.lockout_duration
            }
            
        except Exception as e:
            logger.error(f"Error getting lockout stats: {e}")
            return {
                "currently_locked": 0,
                "users_with_failed_attempts": 0,
                "max_attempts": self.max_attempts,
                "lockout_duration_minutes": self.lockout_duration
            }