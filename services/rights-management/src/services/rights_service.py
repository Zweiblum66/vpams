"""
Rights Management Service - Core Rights Service
"""

import asyncio
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid

from ..models.schemas import (
    RightsPartyCreate, RightsPartyUpdate, RightsPartyResponse,
    LicenseCreate, LicenseUpdate, LicenseResponse, LicenseFilter,
    UsageRecordCreate, UsageRecordUpdate, UsageRecordResponse, UsageRecordFilter,
    PaginatedResponse, User,
    BulkLicenseCreate, BulkLicenseUpdate, BulkUsageRecordCreate, BulkOperationResult
)
from ..models.audit_schemas import (
    AuditTrailCreate, AuditAction, AuditResourceType, AuditContext
)
from ..db.models import RightsParty, License, UsageRecord, LicenseAuditLog
from ..core.config import settings
from ..core.exceptions import RightsError, ValidationError
from ..core.logger import get_logger
from .audit_service import AuditService

logger = get_logger(__name__)


class RightsService:
    """Service for managing rights, licenses, and usage records"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Rights Party methods
    async def create_rights_party(self, party_data: RightsPartyCreate, user: User) -> RightsPartyResponse:
        """Create a new rights party"""
        audit_service = AuditService()
        
        try:
            # Check if party already exists
            existing_party = await self.db.execute(
                select(RightsParty).where(
                    and_(
                        RightsParty.name == party_data.name,
                        RightsParty.party_type == party_data.party_type
                    )
                )
            )
            
            if existing_party.scalar_one_or_none():
                raise ValidationError("Rights party with this name and type already exists")
            
            # Create new party
            party = RightsParty(
                **party_data.dict()
            )
            
            self.db.add(party)
            await self.db.commit()
            await self.db.refresh(party)
            
            # Create audit trail entry
            audit_data = AuditTrailCreate(
                action=AuditAction.PARTY_CREATED,
                resource_type=AuditResourceType.RIGHTS_PARTY,
                resource_id=str(party.id),
                user_id=user.user_id,
                user_email=user.email,
                user_name=user.username,
                user_roles=user.roles,
                new_values=party_data.dict(),
                changes_summary=f"Created rights party: {party.name} ({party.party_type})",
                metadata={
                    "party_type": party.party_type,
                    "party_name": party.name
                },
                tags=["rights_party", "create"],
                success=True
            )
            await audit_service.create_audit_trail(self.db, audit_data)
            
            logger.info(f"Created rights party: {party.id}")
            return RightsPartyResponse.from_orm(party)
            
        except Exception as e:
            await self.db.rollback()
            
            # Log failed attempt in audit trail
            audit_data = AuditTrailCreate(
                action=AuditAction.PARTY_CREATED,
                resource_type=AuditResourceType.RIGHTS_PARTY,
                resource_id="N/A",
                user_id=user.user_id,
                user_email=user.email,
                user_name=user.username,
                user_roles=user.roles,
                new_values=party_data.dict(),
                changes_summary=f"Failed to create rights party: {party_data.name}",
                success=False,
                error_message=str(e)
            )
            await audit_service.create_audit_trail(self.db, audit_data)
            
            logger.error(f"Failed to create rights party: {str(e)}")
            raise RightsError(f"Failed to create rights party: {str(e)}")
    
    async def get_rights_parties(
        self, 
        page: int = 1, 
        limit: int = 20,
        party_type: Optional[str] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> PaginatedResponse:
        """Get rights parties with pagination and filtering"""
        try:
            query = select(RightsParty)
            
            # Apply filters
            if party_type:
                query = query.where(RightsParty.party_type == party_type)
            
            if search:
                query = query.where(
                    or_(
                        RightsParty.name.ilike(f"%{search}%"),
                        RightsParty.legal_name.ilike(f"%{search}%"),
                        RightsParty.contact_email.ilike(f"%{search}%")
                    )
                )
            
            if is_active is not None:
                query = query.where(RightsParty.is_active == is_active)
            
            # Get total count
            count_query = select(func.count(RightsParty.id)).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(RightsParty.created_at)).offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            parties = result.scalars().all()
            
            return PaginatedResponse(
                items=[RightsPartyResponse.from_orm(party) for party in parties],
                total=total,
                page=page,
                limit=limit,
                pages=(total + limit - 1) // limit
            )
            
        except Exception as e:
            logger.error(f"Failed to get rights parties: {str(e)}")
            raise RightsError(f"Failed to get rights parties: {str(e)}")
    
    async def get_rights_party(self, party_id: str) -> Optional[RightsPartyResponse]:
        """Get a specific rights party"""
        try:
            result = await self.db.execute(
                select(RightsParty).where(RightsParty.id == party_id)
            )
            party = result.scalar_one_or_none()
            
            if not party:
                return None
            
            return RightsPartyResponse.from_orm(party)
            
        except Exception as e:
            logger.error(f"Failed to get rights party: {str(e)}")
            raise RightsError(f"Failed to get rights party: {str(e)}")
    
    async def update_rights_party(
        self, 
        party_id: str, 
        party_update: RightsPartyUpdate, 
        user: User
    ) -> Optional[RightsPartyResponse]:
        """Update a rights party"""
        audit_service = AuditService()
        
        try:
            result = await self.db.execute(
                select(RightsParty).where(RightsParty.id == party_id)
            )
            party = result.scalar_one_or_none()
            
            if not party:
                return None
            
            # Capture old values for audit
            old_values = {
                "name": party.name,
                "party_type": party.party_type,
                "legal_name": party.legal_name,
                "contact_email": party.contact_email,
                "contact_phone": party.contact_phone,
                "address": party.address,
                "country": party.country,
                "tax_id": party.tax_id,
                "percentage_share": party.percentage_share,
                "is_active": party.is_active,
                "metadata": party.metadata
            }
            
            # Update fields
            update_data = party_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(party, field, value)
            
            await self.db.commit()
            await self.db.refresh(party)
            
            # Calculate changes for audit
            new_values = {}
            for field, value in update_data.items():
                if old_values.get(field) != value:
                    new_values[field] = value
            
            # Create audit trail entry
            audit_data = AuditTrailCreate(
                action=AuditAction.PARTY_UPDATED,
                resource_type=AuditResourceType.RIGHTS_PARTY,
                resource_id=str(party.id),
                user_id=user.user_id,
                user_email=user.email,
                user_name=user.username,
                user_roles=user.roles,
                old_values=old_values,
                new_values=new_values,
                changes_summary=audit_service.generate_changes_summary(
                    audit_service.calculate_diff(old_values, new_values)
                ),
                metadata={
                    "party_type": party.party_type,
                    "party_name": party.name
                },
                tags=["rights_party", "update"],
                success=True
            )
            await audit_service.create_audit_trail(self.db, audit_data)
            
            logger.info(f"Updated rights party: {party.id}")
            return RightsPartyResponse.from_orm(party)
            
        except Exception as e:
            await self.db.rollback()
            
            # Log failed attempt in audit trail
            audit_data = AuditTrailCreate(
                action=AuditAction.PARTY_UPDATED,
                resource_type=AuditResourceType.RIGHTS_PARTY,
                resource_id=party_id,
                user_id=user.user_id,
                user_email=user.email,
                user_name=user.username,
                user_roles=user.roles,
                old_values={},
                new_values=party_update.dict(exclude_unset=True),
                changes_summary=f"Failed to update rights party",
                success=False,
                error_message=str(e)
            )
            await audit_service.create_audit_trail(self.db, audit_data)
            
            logger.error(f"Failed to update rights party: {str(e)}")
            raise RightsError(f"Failed to update rights party: {str(e)}")
    
    async def delete_rights_party(self, party_id: str, user: User) -> bool:
        """Delete a rights party"""
        audit_service = AuditService()
        
        try:
            result = await self.db.execute(
                select(RightsParty).where(RightsParty.id == party_id)
            )
            party = result.scalar_one_or_none()
            
            if not party:
                return False
            
            # Capture party info for audit
            party_info = {
                "name": party.name,
                "party_type": party.party_type,
                "legal_name": party.legal_name,
                "contact_email": party.contact_email,
                "is_active": party.is_active
            }
            
            # Check if party has active licenses
            license_count = await self.db.execute(
                select(func.count(License.id)).where(
                    or_(
                        License.licensor_id == party_id,
                        License.licensee_id == party_id
                    )
                )
            )
            
            action = None
            changes_summary = ""
            
            if license_count.scalar() > 0:
                # Soft delete - just mark as inactive
                party.is_active = False
                await self.db.commit()
                action = AuditAction.PARTY_DEACTIVATED
                changes_summary = f"Deactivated rights party: {party.name} (has active licenses)"
                logger.info(f"Soft deleted rights party: {party.id}")
            else:
                # Hard delete if no licenses
                await self.db.delete(party)
                await self.db.commit()
                action = AuditAction.PARTY_DELETED
                changes_summary = f"Deleted rights party: {party.name}"
                logger.info(f"Hard deleted rights party: {party.id}")
            
            # Create audit trail entry
            audit_data = AuditTrailCreate(
                action=action,
                resource_type=AuditResourceType.RIGHTS_PARTY,
                resource_id=str(party_id),
                user_id=user.user_id,
                user_email=user.email,
                user_name=user.username,
                user_roles=user.roles,
                old_values=party_info,
                new_values={"is_active": False} if action == AuditAction.PARTY_DEACTIVATED else None,
                changes_summary=changes_summary,
                metadata={
                    "party_type": party.party_type,
                    "party_name": party.name,
                    "license_count": license_count.scalar()
                },
                tags=["rights_party", "delete"],
                success=True
            )
            await audit_service.create_audit_trail(self.db, audit_data)
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            
            # Log failed attempt in audit trail
            audit_data = AuditTrailCreate(
                action=AuditAction.PARTY_DELETED,
                resource_type=AuditResourceType.RIGHTS_PARTY,
                resource_id=party_id,
                user_id=user.user_id,
                user_email=user.email,
                user_name=user.username,
                user_roles=user.roles,
                changes_summary=f"Failed to delete rights party",
                success=False,
                error_message=str(e)
            )
            await audit_service.create_audit_trail(self.db, audit_data)
            
            logger.error(f"Failed to delete rights party: {str(e)}")
            raise RightsError(f"Failed to delete rights party: {str(e)}")
    
    # License methods
    async def create_license(self, license_data: LicenseCreate, user: User) -> LicenseResponse:
        """Create a new license"""
        try:
            # Validate parties exist
            await self._validate_parties(license_data.licensor_id, license_data.licensee_id)
            
            # Check if license number already exists
            existing_license = await self.db.execute(
                select(License).where(License.license_number == license_data.license_number)
            )
            
            if existing_license.scalar_one_or_none():
                raise ValidationError("License number already exists")
            
            # Create new license
            license_dict = license_data.dict()
            license = License(**license_dict)
            
            self.db.add(license)
            await self.db.commit()
            await self.db.refresh(license)
            
            # Create audit log
            await self._create_license_audit_log(
                license.id, 
                "created", 
                user.user_id,
                old_values=None,
                new_values=license_dict
            )
            
            # Load relationships
            await self.db.refresh(license, ["licensor", "licensee"])
            
            logger.info(f"Created license: {license.id}")
            return LicenseResponse.from_orm(license)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create license: {str(e)}")
            raise RightsError(f"Failed to create license: {str(e)}")
    
    async def get_licenses(
        self, 
        page: int = 1, 
        limit: int = 20,
        license_filter: Optional[LicenseFilter] = None
    ) -> PaginatedResponse:
        """Get licenses with pagination and filtering"""
        try:
            query = select(License).options(
                selectinload(License.licensor),
                selectinload(License.licensee)
            )
            
            # Apply filters
            if license_filter:
                query = self._apply_license_filters(query, license_filter)
            
            # Get total count
            count_query = select(func.count(License.id)).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(License.created_at)).offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            licenses = result.scalars().all()
            
            return PaginatedResponse(
                items=[LicenseResponse.from_orm(license) for license in licenses],
                total=total,
                page=page,
                limit=limit,
                pages=(total + limit - 1) // limit
            )
            
        except Exception as e:
            logger.error(f"Failed to get licenses: {str(e)}")
            raise RightsError(f"Failed to get licenses: {str(e)}")
    
    async def get_license(self, license_id: str) -> Optional[LicenseResponse]:
        """Get a specific license"""
        try:
            result = await self.db.execute(
                select(License)
                .options(
                    selectinload(License.licensor),
                    selectinload(License.licensee)
                )
                .where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return None
            
            return LicenseResponse.from_orm(license)
            
        except Exception as e:
            logger.error(f"Failed to get license: {str(e)}")
            raise RightsError(f"Failed to get license: {str(e)}")
    
    async def update_license(
        self, 
        license_id: str, 
        license_update: LicenseUpdate, 
        user: User
    ) -> Optional[LicenseResponse]:
        """Update a license"""
        try:
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return None
            
            # Store old values for audit
            old_values = {
                field: getattr(license, field) 
                for field in license_update.dict(exclude_unset=True).keys()
                if hasattr(license, field)
            }
            
            # Update fields
            update_data = license_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(license, field, value)
            
            await self.db.commit()
            await self.db.refresh(license, ["licensor", "licensee"])
            
            # Create audit log
            await self._create_license_audit_log(
                license.id, 
                "updated", 
                user.user_id,
                old_values=old_values,
                new_values=update_data
            )
            
            logger.info(f"Updated license: {license.id}")
            return LicenseResponse.from_orm(license)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update license: {str(e)}")
            raise RightsError(f"Failed to update license: {str(e)}")
    
    async def delete_license(self, license_id: str, user: User) -> bool:
        """Delete a license"""
        try:
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return False
            
            # Create audit log before deletion
            await self._create_license_audit_log(
                license.id, 
                "deleted", 
                user.user_id,
                old_values=license.__dict__.copy(),
                new_values=None
            )
            
            await self.db.delete(license)
            await self.db.commit()
            
            logger.info(f"Deleted license: {license_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete license: {str(e)}")
            raise RightsError(f"Failed to delete license: {str(e)}")
    
    # Usage Record methods
    async def create_usage_record(self, usage_data: UsageRecordCreate, user: User) -> UsageRecordResponse:
        """Create a new usage record"""
        try:
            # Validate license exists
            license = await self.db.execute(
                select(License).where(License.id == usage_data.license_id)
            )
            
            if not license.scalar_one_or_none():
                raise ValidationError("License not found")
            
            # Create new usage record
            usage_dict = usage_data.dict()
            usage_record = UsageRecord(**usage_dict)
            
            self.db.add(usage_record)
            await self.db.commit()
            await self.db.refresh(usage_record)
            
            # Load relationships
            await self.db.refresh(usage_record, ["license"])
            
            logger.info(f"Created usage record: {usage_record.id}")
            return UsageRecordResponse.from_orm(usage_record)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create usage record: {str(e)}")
            raise RightsError(f"Failed to create usage record: {str(e)}")
    
    async def get_usage_records(
        self, 
        page: int = 1, 
        limit: int = 20,
        usage_filter: Optional[UsageRecordFilter] = None
    ) -> PaginatedResponse:
        """Get usage records with pagination and filtering"""
        try:
            query = select(UsageRecord).options(
                selectinload(UsageRecord.license)
            )
            
            # Apply filters
            if usage_filter:
                query = self._apply_usage_filters(query, usage_filter)
            
            # Get total count
            count_query = select(func.count(UsageRecord.id)).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(UsageRecord.usage_date)).offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            usage_records = result.scalars().all()
            
            return PaginatedResponse(
                items=[UsageRecordResponse.from_orm(record) for record in usage_records],
                total=total,
                page=page,
                limit=limit,
                pages=(total + limit - 1) // limit
            )
            
        except Exception as e:
            logger.error(f"Failed to get usage records: {str(e)}")
            raise RightsError(f"Failed to get usage records: {str(e)}")
    
    async def get_usage_record(self, usage_id: str) -> Optional[UsageRecordResponse]:
        """Get a specific usage record"""
        try:
            result = await self.db.execute(
                select(UsageRecord)
                .options(selectinload(UsageRecord.license))
                .where(UsageRecord.id == usage_id)
            )
            usage_record = result.scalar_one_or_none()
            
            if not usage_record:
                return None
            
            return UsageRecordResponse.from_orm(usage_record)
            
        except Exception as e:
            logger.error(f"Failed to get usage record: {str(e)}")
            raise RightsError(f"Failed to get usage record: {str(e)}")
    
    # Asset-specific methods
    async def get_asset_licenses(self, asset_id: str) -> List[LicenseResponse]:
        """Get all licenses for a specific asset"""
        try:
            result = await self.db.execute(
                select(License)
                .options(
                    selectinload(License.licensor),
                    selectinload(License.licensee)
                )
                .where(License.asset_id == asset_id)
                .order_by(desc(License.created_at))
            )
            licenses = result.scalars().all()
            
            return [LicenseResponse.from_orm(license) for license in licenses]
            
        except Exception as e:
            logger.error(f"Failed to get asset licenses: {str(e)}")
            raise RightsError(f"Failed to get asset licenses: {str(e)}")
    
    async def get_asset_usage(self, asset_id: str) -> List[UsageRecordResponse]:
        """Get all usage records for a specific asset"""
        try:
            result = await self.db.execute(
                select(UsageRecord)
                .options(selectinload(UsageRecord.license))
                .where(UsageRecord.asset_id == asset_id)
                .order_by(desc(UsageRecord.usage_date))
            )
            usage_records = result.scalars().all()
            
            return [UsageRecordResponse.from_orm(record) for record in usage_records]
            
        except Exception as e:
            logger.error(f"Failed to get asset usage: {str(e)}")
            raise RightsError(f"Failed to get asset usage: {str(e)}")
    
    # Bulk operations
    async def bulk_create_licenses(self, bulk_data: BulkLicenseCreate, user: User) -> BulkOperationResult:
        """Bulk create licenses"""
        try:
            result = BulkOperationResult(
                total_processed=len(bulk_data.licenses),
                successful=0,
                failed=0,
                errors=[],
                created_ids=[]
            )
            
            for i, license_data in enumerate(bulk_data.licenses):
                try:
                    if not bulk_data.validate_only:
                        license_response = await self.create_license(license_data, user)
                        result.created_ids.append(license_response.id)
                    
                    result.successful += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append({
                        "index": i,
                        "license_number": license_data.license_number,
                        "error": str(e)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to bulk create licenses: {str(e)}")
            raise RightsError(f"Failed to bulk create licenses: {str(e)}")
    
    async def bulk_update_licenses(self, bulk_data: BulkLicenseUpdate, user: User) -> BulkOperationResult:
        """Bulk update licenses"""
        try:
            result = BulkOperationResult(
                total_processed=len(bulk_data.license_ids),
                successful=0,
                failed=0,
                errors=[],
                updated_ids=[]
            )
            
            for i, license_id in enumerate(bulk_data.license_ids):
                try:
                    if not bulk_data.validate_only:
                        license_response = await self.update_license(license_id, bulk_data.updates, user)
                        if license_response:
                            result.updated_ids.append(license_response.id)
                        else:
                            raise Exception("License not found")
                    
                    result.successful += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append({
                        "index": i,
                        "license_id": license_id,
                        "error": str(e)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to bulk update licenses: {str(e)}")
            raise RightsError(f"Failed to bulk update licenses: {str(e)}")
    
    async def bulk_create_usage_records(self, bulk_data: BulkUsageRecordCreate, user: User) -> BulkOperationResult:
        """Bulk create usage records"""
        try:
            result = BulkOperationResult(
                total_processed=len(bulk_data.usage_records),
                successful=0,
                failed=0,
                errors=[],
                created_ids=[]
            )
            
            for i, usage_data in enumerate(bulk_data.usage_records):
                try:
                    if not bulk_data.validate_only:
                        usage_response = await self.create_usage_record(usage_data, user)
                        result.created_ids.append(usage_response.id)
                    
                    result.successful += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append({
                        "index": i,
                        "license_id": usage_data.license_id,
                        "error": str(e)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to bulk create usage records: {str(e)}")
            raise RightsError(f"Failed to bulk create usage records: {str(e)}")
    
    # Private helper methods
    async def _validate_parties(self, licensor_id: str, licensee_id: str):
        """Validate that parties exist and are active"""
        licensor = await self.db.execute(
            select(RightsParty).where(
                and_(
                    RightsParty.id == licensor_id,
                    RightsParty.is_active == True
                )
            )
        )
        
        licensee = await self.db.execute(
            select(RightsParty).where(
                and_(
                    RightsParty.id == licensee_id,
                    RightsParty.is_active == True
                )
            )
        )
        
        if not licensor.scalar_one_or_none():
            raise ValidationError("Licensor not found or inactive")
        
        if not licensee.scalar_one_or_none():
            raise ValidationError("Licensee not found or inactive")
    
    def _apply_license_filters(self, query, license_filter: LicenseFilter):
        """Apply filters to license query"""
        if license_filter.license_type:
            query = query.where(License.license_type == license_filter.license_type)
        
        if license_filter.status:
            query = query.where(License.status == license_filter.status)
        
        if license_filter.asset_id:
            query = query.where(License.asset_id == license_filter.asset_id)
        
        if license_filter.licensor_id:
            query = query.where(License.licensor_id == license_filter.licensor_id)
        
        if license_filter.licensee_id:
            query = query.where(License.licensee_id == license_filter.licensee_id)
        
        if license_filter.geographic_scope:
            query = query.where(License.geographic_scope == license_filter.geographic_scope)
        
        if license_filter.countries:
            query = query.where(License.countries.overlap(license_filter.countries))
        
        if license_filter.start_date_from:
            query = query.where(License.start_date >= license_filter.start_date_from)
        
        if license_filter.start_date_to:
            query = query.where(License.start_date <= license_filter.start_date_to)
        
        if license_filter.end_date_from:
            query = query.where(License.end_date >= license_filter.end_date_from)
        
        if license_filter.end_date_to:
            query = query.where(License.end_date <= license_filter.end_date_to)
        
        if license_filter.license_fee_min:
            query = query.where(License.license_fee >= license_filter.license_fee_min)
        
        if license_filter.license_fee_max:
            query = query.where(License.license_fee <= license_filter.license_fee_max)
        
        if license_filter.search_text:
            query = query.where(
                or_(
                    License.title.ilike(f"%{license_filter.search_text}%"),
                    License.description.ilike(f"%{license_filter.search_text}%"),
                    License.license_number.ilike(f"%{license_filter.search_text}%")
                )
            )
        
        return query
    
    def _apply_usage_filters(self, query, usage_filter: UsageRecordFilter):
        """Apply filters to usage record query"""
        if usage_filter.license_id:
            query = query.where(UsageRecord.license_id == usage_filter.license_id)
        
        if usage_filter.asset_id:
            query = query.where(UsageRecord.asset_id == usage_filter.asset_id)
        
        if usage_filter.user_id:
            query = query.where(UsageRecord.user_id == usage_filter.user_id)
        
        if usage_filter.usage_type:
            query = query.where(UsageRecord.usage_type == usage_filter.usage_type)
        
        if usage_filter.platform:
            query = query.where(UsageRecord.platform == usage_filter.platform)
        
        if usage_filter.country:
            query = query.where(UsageRecord.country == usage_filter.country)
        
        if usage_filter.usage_date_from:
            query = query.where(UsageRecord.usage_date >= usage_filter.usage_date_from)
        
        if usage_filter.usage_date_to:
            query = query.where(UsageRecord.usage_date <= usage_filter.usage_date_to)
        
        if usage_filter.revenue_min:
            query = query.where(UsageRecord.revenue_generated >= usage_filter.revenue_min)
        
        if usage_filter.revenue_max:
            query = query.where(UsageRecord.revenue_generated <= usage_filter.revenue_max)
        
        if usage_filter.search_text:
            query = query.where(
                or_(
                    UsageRecord.platform.ilike(f"%{usage_filter.search_text}%"),
                    UsageRecord.channel.ilike(f"%{usage_filter.search_text}%"),
                    UsageRecord.program_title.ilike(f"%{usage_filter.search_text}%"),
                    UsageRecord.episode_title.ilike(f"%{usage_filter.search_text}%")
                )
            )
        
        return query
    
    async def _create_license_audit_log(
        self, 
        license_id: str, 
        action: str, 
        user_id: str,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None
    ):
        """Create audit log entry for license changes"""
        try:
            # Determine changed fields
            changed_fields = []
            if old_values and new_values:
                changed_fields = [
                    field for field in new_values.keys() 
                    if old_values.get(field) != new_values.get(field)
                ]
            
            audit_log = LicenseAuditLog(
                license_id=license_id,
                action=action,
                user_id=user_id,
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields
            )
            
            self.db.add(audit_log)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            # Don't raise error for audit log failures