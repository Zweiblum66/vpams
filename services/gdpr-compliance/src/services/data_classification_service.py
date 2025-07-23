"""Data Classification Service for GDPR Compliance"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from uuid import UUID
import logging
import json
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from ..db.models import (
    DataCategory, DataMapping, PrivacyLevel,
    GDPRAuditLog, DataRetentionRule
)
from ..models.schemas import (
    DataCategoryCreate, DataCategoryUpdate, DataCategoryResponse,
    DataMappingCreate, DataMappingUpdate, DataMappingResponse,
    DataClassificationReport, SensitivityLevel,
    DataInventory, DataFlow, ComplianceStatus
)
from ..core.exceptions import (
    DataClassificationError, CategoryNotFoundError,
    MappingNotFoundError
)

logger = logging.getLogger(__name__)


class DataClassificationService:
    """Service for managing data classification and categorization"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ================== Data Category Management ==================
    
    async def create_category(
        self,
        category_data: DataCategoryCreate,
        created_by: str
    ) -> DataCategoryResponse:
        """Create a new data category"""
        try:
            # Check if category already exists
            existing = await self.db.execute(
                select(DataCategory).where(
                    DataCategory.category_name == category_data.category_name
                )
            )
            if existing.scalar_one_or_none():
                raise DataClassificationError(
                    f"Category '{category_data.category_name}' already exists"
                )
            
            # Create category
            category = DataCategory(
                category_name=category_data.category_name,
                description=category_data.description,
                privacy_level=category_data.privacy_level,
                retention_days=category_data.retention_days,
                is_sensitive=category_data.is_sensitive,
                requires_explicit_consent=category_data.requires_explicit_consent,
                can_be_anonymized=category_data.can_be_anonymized,
                legal_basis=category_data.legal_basis,
                purpose=category_data.purpose,
                shared_with_third_parties=category_data.shared_with_third_parties,
                third_party_details=category_data.third_party_details
            )
            
            self.db.add(category)
            
            # Log the creation
            await self._log_activity(
                event_type="data_classification",
                action="create_category",
                actor_id=created_by,
                resource_type="data_category",
                resource_id=str(category.id),
                new_value={"category_name": category.category_name},
                success=True
            )
            
            await self.db.commit()
            await self.db.refresh(category)
            
            return DataCategoryResponse.from_orm(category)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create category: {e}")
            raise DataClassificationError(f"Failed to create category: {str(e)}")
    
    async def get_category(self, category_id: UUID) -> DataCategoryResponse:
        """Get a data category by ID"""
        result = await self.db.execute(
            select(DataCategory)
            .where(DataCategory.id == category_id)
            .options(selectinload(DataCategory.data_mappings))
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise CategoryNotFoundError(f"Category {category_id} not found")
        
        return DataCategoryResponse.from_orm(category)
    
    async def list_categories(
        self,
        privacy_level: Optional[PrivacyLevel] = None,
        is_sensitive: Optional[bool] = None,
        requires_consent: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DataCategoryResponse]:
        """List data categories with filters"""
        query = select(DataCategory)
        
        if privacy_level:
            query = query.where(DataCategory.privacy_level == privacy_level)
        if is_sensitive is not None:
            query = query.where(DataCategory.is_sensitive == is_sensitive)
        if requires_consent is not None:
            query = query.where(
                DataCategory.requires_explicit_consent == requires_consent
            )
        
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        categories = result.scalars().all()
        
        return [DataCategoryResponse.from_orm(cat) for cat in categories]
    
    async def update_category(
        self,
        category_id: UUID,
        update_data: DataCategoryUpdate,
        updated_by: str
    ) -> DataCategoryResponse:
        """Update a data category"""
        category = await self.get_category(category_id)
        
        # Track changes
        old_values = {}
        new_values = {}
        
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            old_val = getattr(category, field)
            if old_val != value:
                old_values[field] = old_val
                new_values[field] = value
        
        if new_values:
            # Apply updates
            await self.db.execute(
                update(DataCategory)
                .where(DataCategory.id == category_id)
                .values(**new_values)
            )
            
            # Log the update
            await self._log_activity(
                event_type="data_classification",
                action="update_category",
                actor_id=updated_by,
                resource_type="data_category",
                resource_id=str(category_id),
                old_value=old_values,
                new_value=new_values,
                success=True
            )
            
            await self.db.commit()
        
        return await self.get_category(category_id)
    
    # ================== Data Mapping Management ==================
    
    async def create_mapping(
        self,
        mapping_data: DataMappingCreate,
        created_by: str
    ) -> DataMappingResponse:
        """Create a new data mapping"""
        try:
            # Verify category exists
            await self.get_category(mapping_data.category_id)
            
            # Check if mapping already exists
            existing = await self.db.execute(
                select(DataMapping).where(
                    and_(
                        DataMapping.table_name == mapping_data.table_name,
                        DataMapping.column_name == mapping_data.column_name
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise DataClassificationError(
                    f"Mapping for {mapping_data.table_name}.{mapping_data.column_name} already exists"
                )
            
            # Create mapping
            mapping = DataMapping(
                table_name=mapping_data.table_name,
                column_name=mapping_data.column_name,
                category_id=mapping_data.category_id,
                field_description=mapping_data.field_description,
                contains_pii=mapping_data.contains_pii,
                encryption_required=mapping_data.encryption_required,
                anonymization_method=mapping_data.anonymization_method,
                anonymization_params=mapping_data.anonymization_params,
                include_in_export=mapping_data.include_in_export,
                export_transform=mapping_data.export_transform
            )
            
            self.db.add(mapping)
            
            # Log the creation
            await self._log_activity(
                event_type="data_classification",
                action="create_mapping",
                actor_id=created_by,
                resource_type="data_mapping",
                resource_id=str(mapping.id),
                new_value={
                    "table": mapping.table_name,
                    "column": mapping.column_name,
                    "category_id": str(mapping.category_id)
                },
                success=True
            )
            
            await self.db.commit()
            await self.db.refresh(mapping)
            
            return DataMappingResponse.from_orm(mapping)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create mapping: {e}")
            raise DataClassificationError(f"Failed to create mapping: {str(e)}")
    
    async def get_mapping(self, mapping_id: UUID) -> DataMappingResponse:
        """Get a data mapping by ID"""
        result = await self.db.execute(
            select(DataMapping)
            .where(DataMapping.id == mapping_id)
            .options(selectinload(DataMapping.category))
        )
        mapping = result.scalar_one_or_none()
        
        if not mapping:
            raise MappingNotFoundError(f"Mapping {mapping_id} not found")
        
        return DataMappingResponse.from_orm(mapping)
    
    async def list_mappings(
        self,
        table_name: Optional[str] = None,
        category_id: Optional[UUID] = None,
        contains_pii: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DataMappingResponse]:
        """List data mappings with filters"""
        query = select(DataMapping).options(selectinload(DataMapping.category))
        
        if table_name:
            query = query.where(DataMapping.table_name == table_name)
        if category_id:
            query = query.where(DataMapping.category_id == category_id)
        if contains_pii is not None:
            query = query.where(DataMapping.contains_pii == contains_pii)
        
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        mappings = result.scalars().all()
        
        return [DataMappingResponse.from_orm(mapping) for mapping in mappings]
    
    # ================== Classification Analysis ==================
    
    async def generate_classification_report(
        self,
        include_mappings: bool = True,
        include_retention: bool = True
    ) -> DataClassificationReport:
        """Generate a comprehensive data classification report"""
        # Get all categories
        categories_result = await self.db.execute(
            select(DataCategory).options(selectinload(DataCategory.data_mappings))
        )
        categories = categories_result.scalars().all()
        
        # Build report
        report = DataClassificationReport(
            generated_at=datetime.utcnow(),
            total_categories=len(categories),
            categories_by_privacy_level={},
            sensitive_data_categories=[],
            third_party_sharing=[],
            retention_summary={},
            unmapped_tables=set(),
            compliance_gaps=[]
        )
        
        # Analyze categories
        privacy_level_counts = defaultdict(int)
        retention_periods = defaultdict(list)
        
        for category in categories:
            privacy_level_counts[category.privacy_level.value] += 1
            
            if category.is_sensitive:
                report.sensitive_data_categories.append({
                    "id": str(category.id),
                    "name": category.category_name,
                    "privacy_level": category.privacy_level.value,
                    "requires_consent": category.requires_explicit_consent,
                    "legal_basis": category.legal_basis
                })
            
            if category.shared_with_third_parties:
                report.third_party_sharing.append({
                    "category": category.category_name,
                    "details": category.third_party_details
                })
            
            if category.retention_days:
                retention_periods[category.retention_days].append(
                    category.category_name
                )
        
        report.categories_by_privacy_level = dict(privacy_level_counts)
        
        # Build retention summary
        for days, categories in retention_periods.items():
            report.retention_summary[f"{days}_days"] = categories
        
        # Check for unmapped critical tables
        critical_tables = [
            "users", "user_profiles", "assets", "metadata",
            "payments", "contracts", "communications"
        ]
        
        if include_mappings:
            mapped_tables_result = await self.db.execute(
                select(DataMapping.table_name).distinct()
            )
            mapped_tables = set(mapped_tables_result.scalars().all())
            
            report.unmapped_tables = set(critical_tables) - mapped_tables
        
        # Identify compliance gaps
        if report.unmapped_tables:
            report.compliance_gaps.append({
                "type": "unmapped_data",
                "severity": "high",
                "description": f"Critical tables without classification: {', '.join(report.unmapped_tables)}",
                "recommendation": "Map all tables containing personal data to appropriate categories"
            })
        
        # Check for categories without retention policies
        no_retention = [
            cat.category_name for cat in categories
            if not cat.retention_days and cat.contains_pii
        ]
        if no_retention:
            report.compliance_gaps.append({
                "type": "missing_retention",
                "severity": "medium",
                "description": f"Categories without retention policies: {', '.join(no_retention)}",
                "recommendation": "Define retention periods for all personal data categories"
            })
        
        return report
    
    async def get_data_inventory(
        self,
        include_flows: bool = True
    ) -> DataInventory:
        """Get a complete inventory of classified data"""
        inventory = DataInventory(
            generated_at=datetime.utcnow(),
            total_tables=0,
            total_columns=0,
            pii_columns=0,
            encrypted_columns=0,
            tables={},
            data_flows=[]
        )
        
        # Get all mappings grouped by table
        mappings_result = await self.db.execute(
            select(DataMapping).options(selectinload(DataMapping.category))
        )
        mappings = mappings_result.scalars().all()
        
        tables_data = defaultdict(lambda: {
            "columns": [],
            "categories": set(),
            "has_pii": False,
            "requires_encryption": False,
            "retention_days": None
        })
        
        for mapping in mappings:
            table_data = tables_data[mapping.table_name]
            
            column_info = {
                "name": mapping.column_name,
                "category": mapping.category.category_name,
                "privacy_level": mapping.category.privacy_level.value,
                "contains_pii": mapping.contains_pii,
                "encrypted": mapping.encryption_required,
                "anonymization": mapping.anonymization_method
            }
            
            table_data["columns"].append(column_info)
            table_data["categories"].add(mapping.category.category_name)
            
            if mapping.contains_pii:
                table_data["has_pii"] = True
                inventory.pii_columns += 1
            
            if mapping.encryption_required:
                table_data["requires_encryption"] = True
                inventory.encrypted_columns += 1
            
            if mapping.category.retention_days:
                if not table_data["retention_days"] or \
                   mapping.category.retention_days < table_data["retention_days"]:
                    table_data["retention_days"] = mapping.category.retention_days
            
            inventory.total_columns += 1
        
        # Convert to final format
        inventory.total_tables = len(tables_data)
        inventory.tables = {
            table: {
                "columns": data["columns"],
                "categories": list(data["categories"]),
                "has_pii": data["has_pii"],
                "requires_encryption": data["requires_encryption"],
                "retention_days": data["retention_days"]
            }
            for table, data in tables_data.items()
        }
        
        # Generate data flows if requested
        if include_flows:
            inventory.data_flows = await self._generate_data_flows(mappings)
        
        return inventory
    
    async def classify_new_data(
        self,
        table_name: str,
        column_info: Dict[str, Any],
        auto_classify: bool = True
    ) -> Optional[DataMappingResponse]:
        """Classify a new data field"""
        # Analyze column for automatic classification
        if auto_classify:
            suggested_category = await self._suggest_category(
                table_name,
                column_info
            )
            
            if suggested_category:
                mapping_data = DataMappingCreate(
                    table_name=table_name,
                    column_name=column_info["name"],
                    category_id=suggested_category.id,
                    field_description=column_info.get("description"),
                    contains_pii=self._is_likely_pii(column_info),
                    encryption_required=self._needs_encryption(column_info),
                    anonymization_method=self._suggest_anonymization(column_info)
                )
                
                return await self.create_mapping(
                    mapping_data,
                    created_by="system_auto_classification"
                )
        
        return None
    
    # ================== Helper Methods ==================
    
    async def _suggest_category(
        self,
        table_name: str,
        column_info: Dict[str, Any]
    ) -> Optional[DataCategory]:
        """Suggest a category based on column characteristics"""
        column_name = column_info.get("name", "").lower()
        data_type = column_info.get("type", "").lower()
        
        # Common patterns for PII
        pii_patterns = {
            "user_identification": ["user_id", "username", "login", "account"],
            "contact_information": ["email", "phone", "address", "contact"],
            "personal_details": ["name", "firstname", "lastname", "surname", "dob", "birthdate"],
            "financial_data": ["payment", "card", "bank", "account_number", "iban"],
            "health_data": ["health", "medical", "diagnosis", "prescription"],
            "biometric_data": ["fingerprint", "face", "retina", "biometric"],
            "location_data": ["location", "gps", "latitude", "longitude", "geolocation"]
        }
        
        # Find matching category
        for category_type, patterns in pii_patterns.items():
            if any(pattern in column_name for pattern in patterns):
                # Look for existing category
                result = await self.db.execute(
                    select(DataCategory).where(
                        DataCategory.category_name.ilike(f"%{category_type}%")
                    )
                )
                category = result.scalar_one_or_none()
                if category:
                    return category
        
        return None
    
    def _is_likely_pii(self, column_info: Dict[str, Any]) -> bool:
        """Determine if column likely contains PII"""
        column_name = column_info.get("name", "").lower()
        
        pii_keywords = [
            "user", "email", "phone", "address", "name", "ssn", "tax",
            "passport", "license", "birth", "gender", "race", "religion",
            "political", "union", "health", "medical", "genetic", "biometric",
            "sexual", "criminal", "payment", "card", "bank", "salary"
        ]
        
        return any(keyword in column_name for keyword in pii_keywords)
    
    def _needs_encryption(self, column_info: Dict[str, Any]) -> bool:
        """Determine if column needs encryption"""
        column_name = column_info.get("name", "").lower()
        
        encryption_keywords = [
            "password", "secret", "key", "token", "ssn", "tax_id",
            "card_number", "bank_account", "medical_record", "health"
        ]
        
        return any(keyword in column_name for keyword in encryption_keywords)
    
    def _suggest_anonymization(self, column_info: Dict[str, Any]) -> str:
        """Suggest anonymization method based on data type"""
        column_name = column_info.get("name", "").lower()
        data_type = column_info.get("type", "").lower()
        
        # Specific anonymization strategies
        if "email" in column_name:
            return "mask_email"
        elif "phone" in column_name:
            return "mask_phone"
        elif any(x in column_name for x in ["name", "firstname", "lastname"]):
            return "pseudonymize"
        elif "address" in column_name:
            return "generalize"
        elif any(x in column_name for x in ["ssn", "tax", "card_number"]):
            return "tokenize"
        elif "date" in data_type or "birth" in column_name:
            return "generalize_date"
        elif any(x in column_name for x in ["salary", "income", "amount"]):
            return "bucket"
        else:
            return "hash"
    
    async def _generate_data_flows(
        self,
        mappings: List[DataMapping]
    ) -> List[DataFlow]:
        """Generate data flow diagrams from mappings"""
        flows = []
        
        # Group by category for flow analysis
        category_tables = defaultdict(set)
        for mapping in mappings:
            category_tables[mapping.category.category_name].add(mapping.table_name)
        
        # Create flows for categories that span multiple tables
        for category, tables in category_tables.items():
            if len(tables) > 1:
                flows.append(DataFlow(
                    category=category,
                    source_tables=list(tables),
                    data_type="cross_table_reference",
                    description=f"Data category '{category}' flows across {len(tables)} tables"
                ))
        
        return flows
    
    async def _log_activity(
        self,
        event_type: str,
        action: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log classification activity"""
        log_entry = GDPRAuditLog(
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            actor_type="system",
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            success=success,
            error_message=error_message
        )
        self.db.add(log_entry)