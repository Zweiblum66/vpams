import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload

from ..models.quantum_key import (
    QuantumKey, KeyStatus, KeyRotation, AlgorithmType,
    QuantumOperation, EncryptedData
)
from ..models.schemas import (
    KeyRotationRequest, KeyRotationResponse, KeyRotationStatus,
    MigrationRequest, MigrationResponse
)
from ..core.config import settings
from .quantum_crypto import QuantumCryptoService

logger = logging.getLogger(__name__)

class KeyManagementService:
    """Service for quantum key lifecycle management."""
    
    def __init__(self):
        self.crypto_service = QuantumCryptoService()
        
    async def rotate_key(
        self,
        db: AsyncSession,
        old_key_id: str,
        reason: str,
        initiated_by: str,
        migrate_data: bool = True
    ) -> KeyRotationResponse:
        """Rotate a quantum key and optionally migrate encrypted data."""
        try:
            # Get the old key
            result = await db.execute(
                select(QuantumKey).where(QuantumKey.key_id == old_key_id)
            )
            old_key = result.scalar_one_or_none()
            
            if not old_key:
                raise ValueError(f"Key {old_key_id} not found")
                
            # Generate new key with same parameters
            new_key = await self.crypto_service.generate_key_pair(
                db=db,
                algorithm=old_key.algorithm,
                owner_id=old_key.owner_id,
                purpose=old_key.purpose,
                enable_hybrid=old_key.classical_algorithm is not None,
                classical_algorithm=old_key.classical_algorithm
            )
            
            # Mark old key as rotated
            old_key.status = KeyStatus.ROTATED
            old_key.rotated_at = datetime.utcnow()
            
            # Count objects to migrate if requested
            objects_to_migrate = 0
            if migrate_data:
                result = await db.execute(
                    select(func.count(EncryptedData.id)).where(
                        EncryptedData.key_id == old_key.id
                    )
                )
                objects_to_migrate = result.scalar() or 0
                
            # Create rotation record
            rotation = KeyRotation(
                rotation_id=f"rot_{uuid.uuid4().hex[:12]}",
                old_key_id=old_key.id,
                new_key_id=new_key.id,
                reason=reason,
                initiated_by=initiated_by,
                migration_status="pending" if migrate_data else "not_required",
                objects_to_migrate=objects_to_migrate
            )
            
            db.add(rotation)
            await db.commit()
            
            # Start migration if requested
            if migrate_data and objects_to_migrate > 0:
                # In production, this would be an async background task
                await self._migrate_encrypted_data(db, rotation.rotation_id)
                
            return KeyRotationResponse(
                rotation_id=rotation.rotation_id,
                old_key_id=old_key_id,
                new_key_id=new_key.key_id,
                new_public_key=new_key.public_key,
                migration_status=rotation.migration_status,
                objects_to_migrate=objects_to_migrate
            )
            
        except Exception as e:
            logger.error(f"Key rotation failed: {str(e)}")
            await db.rollback()
            raise
            
    async def get_rotation_status(
        self,
        db: AsyncSession,
        rotation_id: str
    ) -> KeyRotationStatus:
        """Get the status of a key rotation."""
        result = await db.execute(
            select(KeyRotation).where(KeyRotation.rotation_id == rotation_id)
        )
        rotation = result.scalar_one_or_none()
        
        if not rotation:
            raise ValueError(f"Rotation {rotation_id} not found")
            
        progress_percentage = 0.0
        if rotation.objects_to_migrate > 0:
            progress_percentage = (rotation.objects_migrated / rotation.objects_to_migrate) * 100
            
        # Estimate completion time
        estimated_completion = None
        if rotation.migration_status == "in_progress" and rotation.objects_migrated > 0:
            elapsed = (datetime.utcnow() - rotation.initiated_at).total_seconds()
            rate = rotation.objects_migrated / elapsed
            remaining = rotation.objects_to_migrate - rotation.objects_migrated
            if rate > 0:
                estimated_seconds = remaining / rate
                estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)
                
        return KeyRotationStatus(
            rotation_id=rotation_id,
            migration_status=rotation.migration_status,
            objects_migrated=rotation.objects_migrated,
            objects_to_migrate=rotation.objects_to_migrate,
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion
        )
        
    async def check_key_expiration(self, db: AsyncSession) -> List[QuantumKey]:
        """Check for keys nearing expiration."""
        warning_threshold = datetime.utcnow() + timedelta(days=30)
        
        result = await db.execute(
            select(QuantumKey).where(
                and_(
                    QuantumKey.status == KeyStatus.ACTIVE,
                    QuantumKey.expires_at <= warning_threshold
                )
            )
        )
        
        return result.scalars().all()
        
    async def revoke_key(
        self,
        db: AsyncSession,
        key_id: str,
        reason: str
    ) -> QuantumKey:
        """Revoke a quantum key."""
        try:
            result = await db.execute(
                select(QuantumKey).where(QuantumKey.key_id == key_id)
            )
            key = result.scalar_one_or_none()
            
            if not key:
                raise ValueError(f"Key {key_id} not found")
                
            if key.status != KeyStatus.ACTIVE:
                raise ValueError(f"Key {key_id} is not active")
                
            key.status = KeyStatus.REVOKED
            
            await db.commit()
            await db.refresh(key)
            
            logger.info(f"Revoked key {key_id} for reason: {reason}")
            return key
            
        except Exception as e:
            logger.error(f"Key revocation failed: {str(e)}")
            await db.rollback()
            raise
            
    async def cleanup_expired_keys(self, db: AsyncSession) -> int:
        """Mark expired keys and return count."""
        try:
            result = await db.execute(
                update(QuantumKey)
                .where(
                    and_(
                        QuantumKey.status == KeyStatus.ACTIVE,
                        QuantumKey.expires_at <= datetime.utcnow()
                    )
                )
                .values(status=KeyStatus.EXPIRED)
                .returning(QuantumKey.id)
            )
            
            expired_count = len(result.all())
            await db.commit()
            
            logger.info(f"Marked {expired_count} keys as expired")
            return expired_count
            
        except Exception as e:
            logger.error(f"Key cleanup failed: {str(e)}")
            await db.rollback()
            raise
            
    async def get_key_metrics(
        self,
        db: AsyncSession,
        owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get key management metrics."""
        # Base query
        query = select(QuantumKey)
        if owner_id:
            query = query.where(QuantumKey.owner_id == owner_id)
            
        # Count keys by status
        status_counts = {}
        for status in KeyStatus:
            count_query = query.where(QuantumKey.status == status)
            result = await db.execute(select(func.count()).select_from(count_query.subquery()))
            status_counts[status.value] = result.scalar() or 0
            
        # Count keys by algorithm
        algorithm_counts = {}
        for algorithm in AlgorithmType:
            count_query = query.where(QuantumKey.algorithm == algorithm)
            result = await db.execute(select(func.count()).select_from(count_query.subquery()))
            count = result.scalar() or 0
            if count > 0:
                algorithm_counts[algorithm.value] = count
                
        # Get average quantum resistance score
        result = await db.execute(
            select(func.avg(QuantumKey.quantum_resistance_score))
            .select_from(query.where(QuantumKey.status == KeyStatus.ACTIVE).subquery())
        )
        avg_quantum_resistance = result.scalar() or 0
        
        # Get key rotation compliance (keys rotated within rotation period)
        rotation_deadline = datetime.utcnow() - timedelta(days=settings.key_rotation_days)
        
        result = await db.execute(
            select(func.count())
            .select_from(
                query.where(
                    and_(
                        QuantumKey.status == KeyStatus.ACTIVE,
                        or_(
                            QuantumKey.created_at >= rotation_deadline,
                            QuantumKey.rotated_at >= rotation_deadline
                        )
                    )
                ).subquery()
            )
        )
        compliant_keys = result.scalar() or 0
        
        total_active = status_counts.get(KeyStatus.ACTIVE.value, 0)
        rotation_compliance = (compliant_keys / total_active * 100) if total_active > 0 else 100
        
        return {
            "status_counts": status_counts,
            "algorithm_counts": algorithm_counts,
            "total_keys": sum(status_counts.values()),
            "active_keys": status_counts.get(KeyStatus.ACTIVE.value, 0),
            "average_quantum_resistance": round(avg_quantum_resistance, 2),
            "rotation_compliance_percentage": round(rotation_compliance, 2),
            "keys_expiring_soon": len(await self.check_key_expiration(db))
        }
        
    async def plan_migration(
        self,
        db: AsyncSession,
        source_algorithm: AlgorithmType,
        target_algorithm: AlgorithmType,
        key_pattern: Optional[str] = None
    ) -> MigrationResponse:
        """Plan a migration from one algorithm to another."""
        # Build query
        query = select(QuantumKey).where(
            and_(
                QuantumKey.status == KeyStatus.ACTIVE,
                QuantumKey.algorithm == source_algorithm
            )
        )
        
        if key_pattern:
            query = query.where(QuantumKey.key_id.like(key_pattern))
            
        result = await db.execute(query)
        keys_to_migrate = len(result.scalars().all())
        
        # Estimate time (assume 100ms per key)
        estimated_time_minutes = (keys_to_migrate * 0.1) / 60
        
        migration_id = f"mig_{uuid.uuid4().hex[:12]}"
        
        return MigrationResponse(
            migration_id=migration_id,
            keys_to_migrate=keys_to_migrate,
            estimated_time_minutes=round(estimated_time_minutes, 2),
            dry_run=True
        )
        
    async def _migrate_encrypted_data(
        self,
        db: AsyncSession,
        rotation_id: str
    ) -> None:
        """Migrate encrypted data from old key to new key."""
        try:
            # Get rotation record
            result = await db.execute(
                select(KeyRotation)
                .options(
                    selectinload(KeyRotation.old_key),
                    selectinload(KeyRotation.new_key)
                )
                .where(KeyRotation.rotation_id == rotation_id)
            )
            rotation = result.scalar_one_or_none()
            
            if not rotation:
                raise ValueError(f"Rotation {rotation_id} not found")
                
            # Update status
            rotation.migration_status = "in_progress"
            await db.commit()
            
            # Get encrypted data using old key
            result = await db.execute(
                select(EncryptedData).where(
                    EncryptedData.key_id == rotation.old_key_id
                ).limit(100)  # Process in batches
            )
            
            encrypted_items = result.scalars().all()
            
            for item in encrypted_items:
                try:
                    # Decrypt with old key (simulation)
                    # In production, actually decrypt and re-encrypt
                    
                    # Update to use new key
                    item.key_id = rotation.new_key_id
                    rotation.objects_migrated += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate item {item.data_id}: {str(e)}")
                    continue
                    
            # Check if migration is complete
            if rotation.objects_migrated >= rotation.objects_to_migrate:
                rotation.migration_status = "completed"
                rotation.completed_at = datetime.utcnow()
            else:
                # Schedule next batch (in production)
                pass
                
            await db.commit()
            
        except Exception as e:
            logger.error(f"Data migration failed: {str(e)}")
            # Update migration status
            if rotation:
                rotation.migration_status = "failed"
                await db.commit()
            raise