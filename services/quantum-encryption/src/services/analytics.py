import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from collections import Counter

from ..models.quantum_key import (
    QuantumKey, QuantumOperation, AlgorithmType, KeyStatus
)
from ..models.schemas import (
    QuantumMetrics, AlgorithmStats, SecurityAssessment, SecurityLevel
)
from ..core.config import settings

logger = logging.getLogger(__name__)

class QuantumAnalyticsService:
    """Service for quantum encryption analytics and monitoring."""
    
    async def get_metrics(
        self,
        db: AsyncSession,
        owner_id: Optional[str] = None
    ) -> QuantumMetrics:
        """Get comprehensive quantum encryption metrics."""
        try:
            # Base queries
            key_query = select(QuantumKey)
            op_query = select(QuantumOperation)
            
            if owner_id:
                key_query = key_query.where(QuantumKey.owner_id == owner_id)
                op_query = op_query.join(QuantumKey).where(QuantumKey.owner_id == owner_id)
                
            # Total keys
            result = await db.execute(
                select(func.count(QuantumKey.id)).select_from(key_query.subquery())
            )
            total_keys = result.scalar() or 0
            
            # Active keys
            result = await db.execute(
                select(func.count(QuantumKey.id)).where(
                    QuantumKey.status == KeyStatus.ACTIVE
                ).select_from(key_query.subquery())
            )
            active_keys = result.scalar() or 0
            
            # Operations today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            result = await db.execute(
                select(func.count(QuantumOperation.id)).where(
                    QuantumOperation.created_at >= today_start
                ).select_from(op_query.subquery())
            )
            operations_today = result.scalar() or 0
            
            # Operations this month
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            result = await db.execute(
                select(func.count(QuantumOperation.id)).where(
                    QuantumOperation.created_at >= month_start
                ).select_from(op_query.subquery())
            )
            operations_this_month = result.scalar() or 0
            
            # Average operation time
            result = await db.execute(
                select(func.avg(QuantumOperation.operation_time_ms)).where(
                    QuantumOperation.operation_time_ms.isnot(None)
                ).select_from(op_query.subquery())
            )
            avg_operation_time = result.scalar() or 0
            
            # Most used algorithm
            result = await db.execute(
                select(
                    QuantumKey.algorithm,
                    func.count(QuantumOperation.id).label('count')
                )
                .select_from(op_query.join(QuantumKey).subquery())
                .group_by(QuantumKey.algorithm)
                .order_by(func.count(QuantumOperation.id).desc())
                .limit(1)
            )
            row = result.first()
            most_used_algorithm = row.algorithm if row else AlgorithmType.KYBER1024
            
            # Average quantum resistance score
            result = await db.execute(
                select(func.avg(QuantumKey.quantum_resistance_score)).where(
                    QuantumKey.status == KeyStatus.ACTIVE
                ).select_from(key_query.subquery())
            )
            quantum_resistance_avg = result.scalar() or 0
            
            # Key rotation compliance
            rotation_compliance = await self._calculate_rotation_compliance(db, owner_id)
            
            return QuantumMetrics(
                total_keys=total_keys,
                active_keys=active_keys,
                operations_today=operations_today,
                operations_this_month=operations_this_month,
                average_operation_time_ms=round(avg_operation_time, 2),
                most_used_algorithm=most_used_algorithm,
                quantum_resistance_average=round(quantum_resistance_avg, 2),
                key_rotation_compliance=round(rotation_compliance, 2)
            )
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {str(e)}")
            raise
            
    async def get_algorithm_stats(
        self,
        db: AsyncSession,
        limit: int = 10
    ) -> List[AlgorithmStats]:
        """Get statistics for each algorithm."""
        try:
            # Get usage stats for each algorithm
            result = await db.execute(
                select(
                    QuantumOperation.algorithm_used,
                    func.count(QuantumOperation.id).label('usage_count'),
                    func.avg(QuantumOperation.operation_time_ms).label('avg_time'),
                    func.sum(func.cast(QuantumOperation.success, type_=db.Integer)).label('success_count')
                )
                .where(QuantumOperation.algorithm_used.isnot(None))
                .group_by(QuantumOperation.algorithm_used)
                .order_by(func.count(QuantumOperation.id).desc())
                .limit(limit)
            )
            
            stats = []
            for row in result:
                success_rate = (row.success_count / row.usage_count * 100) if row.usage_count > 0 else 0
                
                # Get security level for algorithm
                security_level = self._get_algorithm_security_level(row.algorithm_used)
                
                stats.append(AlgorithmStats(
                    algorithm=row.algorithm_used,
                    usage_count=row.usage_count,
                    average_operation_time_ms=round(row.avg_time or 0, 2),
                    success_rate=round(success_rate, 2),
                    security_level=security_level
                ))
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get algorithm stats: {str(e)}")
            raise
            
    async def get_security_assessment(
        self,
        db: AsyncSession,
        owner_id: Optional[str] = None
    ) -> SecurityAssessment:
        """Get comprehensive security assessment."""
        try:
            recommendations = []
            vulnerabilities = []
            
            # Get metrics
            metrics = await self.get_metrics(db, owner_id)
            
            # Calculate quantum readiness
            quantum_readiness = metrics.quantum_resistance_average
            
            # Check for classical algorithms in use
            result = await db.execute(
                select(func.count(QuantumKey.id)).where(
                    and_(
                        QuantumKey.status == KeyStatus.ACTIVE,
                        QuantumKey.algorithm.in_([
                            AlgorithmType.RSA2048,
                            AlgorithmType.RSA4096,
                            AlgorithmType.ECC_P256,
                            AlgorithmType.ECC_P384,
                            AlgorithmType.ECC_P521
                        ])
                    )
                )
            )
            classical_key_count = result.scalar() or 0
            
            if classical_key_count > 0:
                vulnerabilities.append(
                    f"{classical_key_count} active keys using classical algorithms vulnerable to quantum attacks"
                )
                recommendations.append(
                    "Migrate classical RSA/ECC keys to quantum-resistant algorithms"
                )
                
            # Check key rotation health
            key_rotation_health = metrics.key_rotation_compliance
            
            if key_rotation_health < 80:
                vulnerabilities.append(
                    f"Key rotation compliance is low ({key_rotation_health}%)"
                )
                recommendations.append(
                    "Enable automatic key rotation for all active keys"
                )
                
            # Check for expired keys still in use
            result = await db.execute(
                select(func.count(QuantumOperation.id)).where(
                    and_(
                        QuantumOperation.created_at >= datetime.utcnow() - timedelta(days=7),
                        QuantumOperation.key.has(QuantumKey.status == KeyStatus.EXPIRED)
                    )
                )
            )
            expired_key_usage = result.scalar() or 0
            
            if expired_key_usage > 0:
                vulnerabilities.append(
                    f"{expired_key_usage} operations using expired keys in the last 7 days"
                )
                recommendations.append(
                    "Review and rotate all expired keys immediately"
                )
                
            # Calculate algorithm diversity
            result = await db.execute(
                select(func.count(func.distinct(QuantumKey.algorithm))).where(
                    QuantumKey.status == KeyStatus.ACTIVE
                )
            )
            unique_algorithms = result.scalar() or 0
            
            algorithm_diversity = min(unique_algorithms / 5 * 100, 100)  # 5 algorithms = 100%
            
            if algorithm_diversity < 60:
                recommendations.append(
                    "Increase algorithm diversity to reduce single-point-of-failure risk"
                )
                
            # Check for weak security levels
            result = await db.execute(
                select(func.count(QuantumKey.id)).where(
                    and_(
                        QuantumKey.status == KeyStatus.ACTIVE,
                        QuantumKey.security_level < 3
                    )
                )
            )
            weak_keys = result.scalar() or 0
            
            if weak_keys > 0:
                vulnerabilities.append(
                    f"{weak_keys} active keys with security level below NIST Level 3"
                )
                recommendations.append(
                    "Upgrade keys to minimum NIST Security Level 3 (256-bit equivalent)"
                )
                
            # Calculate overall score
            overall_score = (
                quantum_readiness * 0.4 +
                key_rotation_health * 0.3 +
                algorithm_diversity * 0.2 +
                (100 - min(len(vulnerabilities) * 10, 50)) * 0.1
            )
            
            return SecurityAssessment(
                overall_score=round(overall_score, 2),
                quantum_readiness=round(quantum_readiness, 2),
                key_rotation_health=round(key_rotation_health, 2),
                algorithm_diversity=round(algorithm_diversity, 2),
                recommendations=recommendations,
                vulnerabilities=vulnerabilities
            )
            
        except Exception as e:
            logger.error(f"Failed to get security assessment: {str(e)}")
            raise
            
    async def get_operation_trends(
        self,
        db: AsyncSession,
        days: int = 30,
        operation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get operation trends over time."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Build query
            query = select(
                func.date(QuantumOperation.created_at).label('date'),
                func.count(QuantumOperation.id).label('count'),
                func.avg(QuantumOperation.operation_time_ms).label('avg_time')
            ).where(
                QuantumOperation.created_at >= start_date
            )
            
            if operation_type:
                query = query.where(QuantumOperation.operation_type == operation_type)
                
            query = query.group_by(func.date(QuantumOperation.created_at))
            query = query.order_by(func.date(QuantumOperation.created_at))
            
            result = await db.execute(query)
            
            trends = []
            for row in result:
                trends.append({
                    "date": row.date.isoformat(),
                    "operations": row.count,
                    "average_time_ms": round(row.avg_time or 0, 2)
                })
                
            return {
                "period_days": days,
                "operation_type": operation_type or "all",
                "trends": trends
            }
            
        except Exception as e:
            logger.error(f"Failed to get operation trends: {str(e)}")
            raise
            
    async def _calculate_rotation_compliance(
        self,
        db: AsyncSession,
        owner_id: Optional[str] = None
    ) -> float:
        """Calculate key rotation compliance percentage."""
        try:
            rotation_deadline = datetime.utcnow() - timedelta(days=settings.key_rotation_days)
            
            # Build base query
            query = select(QuantumKey).where(QuantumKey.status == KeyStatus.ACTIVE)
            if owner_id:
                query = query.where(QuantumKey.owner_id == owner_id)
                
            # Count total active keys
            result = await db.execute(
                select(func.count(QuantumKey.id)).select_from(query.subquery())
            )
            total_active = result.scalar() or 0
            
            if total_active == 0:
                return 100.0
                
            # Count compliant keys
            compliant_query = query.where(
                or_(
                    QuantumKey.created_at >= rotation_deadline,
                    and_(
                        QuantumKey.rotated_at.isnot(None),
                        QuantumKey.rotated_at >= rotation_deadline
                    )
                )
            )
            
            result = await db.execute(
                select(func.count(QuantumKey.id)).select_from(compliant_query.subquery())
            )
            compliant_count = result.scalar() or 0
            
            return (compliant_count / total_active) * 100
            
        except Exception as e:
            logger.error(f"Failed to calculate rotation compliance: {str(e)}")
            return 0.0
            
    def _get_algorithm_security_level(self, algorithm: AlgorithmType) -> SecurityLevel:
        """Get security level for an algorithm."""
        security_levels = {
            # Quantum-resistant algorithms
            AlgorithmType.KYBER512: SecurityLevel.LEVEL_1,
            AlgorithmType.KYBER768: SecurityLevel.LEVEL_2,
            AlgorithmType.KYBER1024: SecurityLevel.LEVEL_3,
            AlgorithmType.DILITHIUM2: SecurityLevel.LEVEL_1,
            AlgorithmType.DILITHIUM3: SecurityLevel.LEVEL_3,
            AlgorithmType.DILITHIUM5: SecurityLevel.LEVEL_5,
            AlgorithmType.FALCON512: SecurityLevel.LEVEL_1,
            AlgorithmType.FALCON1024: SecurityLevel.LEVEL_5,
            AlgorithmType.SPHINCS_SHA256_128F: SecurityLevel.LEVEL_1,
            AlgorithmType.SPHINCS_SHA256_192F: SecurityLevel.LEVEL_3,
            AlgorithmType.SPHINCS_SHA256_256F: SecurityLevel.LEVEL_5,
            AlgorithmType.NTRU_HPS2048509: SecurityLevel.LEVEL_1,
            AlgorithmType.NTRU_HPS2048677: SecurityLevel.LEVEL_3,
            AlgorithmType.NTRU_HPS4096821: SecurityLevel.LEVEL_5,
            AlgorithmType.SABER_LIGHT: SecurityLevel.LEVEL_1,
            AlgorithmType.SABER: SecurityLevel.LEVEL_3,
            AlgorithmType.SABER_FIRE: SecurityLevel.LEVEL_5,
            # Classical algorithms
            AlgorithmType.RSA2048: SecurityLevel.LEVEL_1,
            AlgorithmType.RSA4096: SecurityLevel.LEVEL_2,
            AlgorithmType.ECC_P256: SecurityLevel.LEVEL_1,
            AlgorithmType.ECC_P384: SecurityLevel.LEVEL_2,
            AlgorithmType.ECC_P521: SecurityLevel.LEVEL_3,
            AlgorithmType.AES256: SecurityLevel.LEVEL_3,
        }
        
        return security_levels.get(algorithm, SecurityLevel.LEVEL_1)