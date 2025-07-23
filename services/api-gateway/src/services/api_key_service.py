"""
API Key Management Service

Handles creation, validation, and management of API keys.
"""

import secrets
import hashlib
import re
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import logging

from db.models import APIKey, APIKeyUsageLog, GatewayAuditLog
from core.exceptions import ValidationException, DuplicateException, NotFoundException
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class APIKeyService:
    """Service for managing API keys"""
    
    # API key configuration
    KEY_PREFIX = "mams_"
    KEY_LENGTH = 32  # Length of random part
    HASH_ALGORITHM = "sha256"
    
    # Default scopes
    DEFAULT_SCOPES = ["read"]
    ADMIN_SCOPES = ["read", "write", "admin"]
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_api_key(
        self,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_override: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[APIKey, str]:
        """
        Create a new API key
        
        Args:
            name: Name for the API key
            description: Optional description
            user_id: Optional user association
            application_id: Optional application association
            scopes: List of permission scopes
            expires_in_days: Optional expiration in days
            rate_limit_override: Optional custom rate limit
            metadata: Optional metadata
            
        Returns:
            Tuple of (APIKey model, raw key string)
        """
        # Validate name
        if not name or len(name) < 3:
            raise ValidationException("API key name must be at least 3 characters")
        
        # Generate the raw key
        raw_key = self._generate_key()
        full_key = f"{self.KEY_PREFIX}{raw_key}"
        
        # Extract key parts
        key_hash = self._hash_key(full_key)
        last_four = raw_key[-4:]
        
        # Set expiration if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create the API key model
        api_key = APIKey(
            key=full_key[:16],  # Store only prefix + first part for identification
            name=name,
            description=description,
            prefix=self.KEY_PREFIX,
            hash=key_hash,
            last_four=last_four,
            user_id=user_id,
            application_id=application_id,
            scopes=scopes or self.DEFAULT_SCOPES,
            expires_at=expires_at,
            rate_limit_override=rate_limit_override,
            metadata=metadata or {}
        )
        
        # Save to database
        self.db.add(api_key)
        
        try:
            await self.db.commit()
            await self.db.refresh(api_key)
            
            # Log the creation
            await self._log_audit_event(
                event_type="api_key_created",
                event_category="security",
                severity="info",
                resource_type="api_key",
                resource_id=str(api_key.id),
                details={
                    "name": name,
                    "user_id": user_id,
                    "application_id": application_id,
                    "scopes": scopes or self.DEFAULT_SCOPES
                }
            )
            
            return api_key, full_key
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create API key: {e}")
            raise
    
    async def validate_api_key(self, key: str) -> Optional[APIKey]:
        """
        Validate an API key and return the associated model
        
        Args:
            key: The full API key string
            
        Returns:
            APIKey model if valid, None otherwise
        """
        if not key or not key.startswith(self.KEY_PREFIX):
            return None
        
        # Hash the provided key
        key_hash = self._hash_key(key)
        
        # Query for active key with matching hash
        query = select(APIKey).where(
            and_(
                APIKey.hash == key_hash,
                APIKey.is_active == True,
                or_(
                    APIKey.expires_at.is_(None),
                    APIKey.expires_at > datetime.utcnow()
                )
            )
        )
        
        result = await self.db.execute(query)
        api_key = result.scalar_one_or_none()
        
        if api_key:
            # Update last used timestamp
            api_key.last_used_at = datetime.utcnow()
            api_key.usage_count += 1
            await self.db.commit()
        
        return api_key
    
    async def get_api_key(self, key_id: str) -> APIKey:
        """
        Get an API key by ID
        
        Args:
            key_id: The API key ID
            
        Returns:
            APIKey model
            
        Raises:
            NotFoundException: If key not found
        """
        query = select(APIKey).where(APIKey.id == key_id)
        result = await self.db.execute(query)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise NotFoundException(f"API key {key_id} not found")
        
        return api_key
    
    async def list_api_keys(
        self,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[APIKey], int]:
        """
        List API keys with optional filters
        
        Args:
            user_id: Filter by user
            application_id: Filter by application
            is_active: Filter by active status
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (list of API keys, total count)
        """
        # Build query
        query = select(APIKey)
        count_query = select(func.count()).select_from(APIKey)
        
        # Apply filters
        filters = []
        if user_id is not None:
            filters.append(APIKey.user_id == user_id)
        if application_id is not None:
            filters.append(APIKey.application_id == application_id)
        if is_active is not None:
            filters.append(APIKey.is_active == is_active)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination and get results
        query = query.offset(skip).limit(limit).order_by(APIKey.created_at.desc())
        result = await self.db.execute(query)
        api_keys = result.scalars().all()
        
        return api_keys, total_count
    
    async def update_api_key(
        self,
        key_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        rate_limit_override: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIKey:
        """
        Update an API key
        
        Args:
            key_id: The API key ID
            name: New name
            description: New description
            scopes: New scopes
            rate_limit_override: New rate limit
            metadata: New metadata
            
        Returns:
            Updated APIKey model
        """
        api_key = await self.get_api_key(key_id)
        
        # Update fields
        if name is not None:
            api_key.name = name
        if description is not None:
            api_key.description = description
        if scopes is not None:
            api_key.scopes = scopes
        if rate_limit_override is not None:
            api_key.rate_limit_override = rate_limit_override
        if metadata is not None:
            api_key.metadata = metadata
        
        api_key.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(api_key)
        
        # Log the update
        await self._log_audit_event(
            event_type="api_key_updated",
            event_category="security",
            severity="info",
            resource_type="api_key",
            resource_id=str(api_key.id),
            details={
                "updated_fields": [
                    field for field in ["name", "description", "scopes", "rate_limit_override", "metadata"]
                    if locals()[field] is not None
                ]
            }
        )
        
        return api_key
    
    async def revoke_api_key(self, key_id: str, reason: Optional[str] = None) -> APIKey:
        """
        Revoke an API key
        
        Args:
            key_id: The API key ID
            reason: Optional revocation reason
            
        Returns:
            Revoked APIKey model
        """
        api_key = await self.get_api_key(key_id)
        
        if not api_key.is_active:
            raise ValidationException("API key is already revoked")
        
        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_reason = reason
        
        await self.db.commit()
        await self.db.refresh(api_key)
        
        # Log the revocation
        await self._log_audit_event(
            event_type="api_key_revoked",
            event_category="security",
            severity="warning",
            resource_type="api_key",
            resource_id=str(api_key.id),
            details={
                "reason": reason
            }
        )
        
        return api_key
    
    async def rotate_api_key(
        self,
        key_id: str,
        revoke_old: bool = True
    ) -> Tuple[APIKey, str]:
        """
        Rotate an API key by creating a new one with same settings
        
        Args:
            key_id: The API key ID to rotate
            revoke_old: Whether to revoke the old key
            
        Returns:
            Tuple of (new APIKey model, raw key string)
        """
        old_key = await self.get_api_key(key_id)
        
        # Create new key with same settings
        new_key, raw_key = await self.create_api_key(
            name=f"{old_key.name} (rotated)",
            description=old_key.description,
            user_id=old_key.user_id,
            application_id=old_key.application_id,
            scopes=old_key.scopes,
            expires_in_days=None,  # Will calculate from old key
            rate_limit_override=old_key.rate_limit_override,
            metadata={**old_key.metadata, "rotated_from": str(old_key.id)}
        )
        
        # Set same expiration if exists
        if old_key.expires_at:
            days_until_expiry = (old_key.expires_at - datetime.utcnow()).days
            if days_until_expiry > 0:
                new_key.expires_at = old_key.expires_at
                await self.db.commit()
        
        # Revoke old key if requested
        if revoke_old:
            await self.revoke_api_key(key_id, reason="Rotated")
        
        return new_key, raw_key
    
    async def log_api_key_usage(
        self,
        api_key_id: str,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> None:
        """
        Log API key usage
        
        Args:
            api_key_id: The API key ID
            request_id: Request ID
            method: HTTP method
            path: Request path
            status_code: Response status code
            ip_address: Client IP
            user_agent: User agent
            response_time_ms: Response time in milliseconds
        """
        usage_log = APIKeyUsageLog(
            api_key_id=api_key_id,
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
            response_time_ms=response_time_ms
        )
        
        self.db.add(usage_log)
        await self.db.commit()
    
    async def get_api_key_usage_stats(
        self,
        key_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for an API key
        
        Args:
            key_id: The API key ID
            days: Number of days to look back
            
        Returns:
            Dictionary of usage statistics
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get usage logs
        query = select(APIKeyUsageLog).where(
            and_(
                APIKeyUsageLog.api_key_id == key_id,
                APIKeyUsageLog.created_at >= since
            )
        )
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        # Calculate statistics
        total_requests = len(logs)
        successful_requests = sum(1 for log in logs if 200 <= log.status_code < 300)
        failed_requests = sum(1 for log in logs if log.status_code >= 400)
        
        # Group by status code
        status_codes = {}
        for log in logs:
            status_codes[log.status_code] = status_codes.get(log.status_code, 0) + 1
        
        # Calculate average response time
        response_times = [log.response_time_ms for log in logs if log.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "status_codes": status_codes,
            "average_response_time_ms": avg_response_time,
            "period_days": days,
            "since": since.isoformat()
        }
    
    def _generate_key(self) -> str:
        """Generate a secure random API key"""
        return secrets.token_urlsafe(self.KEY_LENGTH)
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    async def _log_audit_event(
        self,
        event_type: str,
        event_category: str,
        severity: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an audit event"""
        audit_log = GatewayAuditLog(
            event_type=event_type,
            event_category=event_category,
            severity=severity,
            actor_type="system",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {}
        )
        
        self.db.add(audit_log)
        # Don't commit here, let the main transaction handle it