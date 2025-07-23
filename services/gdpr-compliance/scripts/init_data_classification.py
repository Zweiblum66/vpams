"""Initialize default data classification categories and mappings"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.services.data_classification_service import DataClassificationService
from src.models.schemas import DataCategoryCreate, DataMappingCreate, PrivacyLevel
from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEFAULT_CATEGORIES = [
    # User Identification
    DataCategoryCreate(
        category_name="User Identification",
        description="Data that directly identifies users (usernames, IDs, etc.)",
        privacy_level=PrivacyLevel.CONFIDENTIAL,
        retention_days=2555,  # 7 years
        is_sensitive=False,
        requires_explicit_consent=False,
        can_be_anonymized=False,
        legal_basis="contract",
        purpose="User account management and authentication",
        shared_with_third_parties=False
    ),
    
    # Contact Information
    DataCategoryCreate(
        category_name="Contact Information",
        description="User contact details (email, phone, address)",
        privacy_level=PrivacyLevel.CONFIDENTIAL,
        retention_days=2555,
        is_sensitive=False,
        requires_explicit_consent=False,
        can_be_anonymized=True,
        legal_basis="contract",
        purpose="Communication with users and service delivery",
        shared_with_third_parties=False
    ),
    
    # Personal Details
    DataCategoryCreate(
        category_name="Personal Details",
        description="Personal information (name, DOB, gender, etc.)",
        privacy_level=PrivacyLevel.CONFIDENTIAL,
        retention_days=2555,
        is_sensitive=False,
        requires_explicit_consent=False,
        can_be_anonymized=True,
        legal_basis="contract",
        purpose="User profile management",
        shared_with_third_parties=False
    ),
    
    # Authentication Data
    DataCategoryCreate(
        category_name="Authentication Data",
        description="Passwords, tokens, and security credentials",
        privacy_level=PrivacyLevel.RESTRICTED,
        retention_days=365,  # 1 year after change
        is_sensitive=True,
        requires_explicit_consent=False,
        can_be_anonymized=False,
        legal_basis="contract",
        purpose="Account security and access control",
        shared_with_third_parties=False
    ),
    
    # Financial Data
    DataCategoryCreate(
        category_name="Financial Information",
        description="Payment methods, transaction history, billing data",
        privacy_level=PrivacyLevel.RESTRICTED,
        retention_days=3650,  # 10 years for tax compliance
        is_sensitive=True,
        requires_explicit_consent=True,
        can_be_anonymized=False,
        legal_basis="legal_obligation",
        purpose="Payment processing and financial compliance",
        shared_with_third_parties=True,
        third_party_details={
            "processors": ["Payment Gateway", "Accounting Software"],
            "purpose": "Payment processing and bookkeeping"
        }
    ),
    
    # Usage Data
    DataCategoryCreate(
        category_name="Usage Analytics",
        description="System usage patterns and behavior",
        privacy_level=PrivacyLevel.INTERNAL,
        retention_days=730,  # 2 years
        is_sensitive=False,
        requires_explicit_consent=False,
        can_be_anonymized=True,
        legal_basis="legitimate_interest",
        purpose="Service improvement and analytics",
        shared_with_third_parties=False
    ),
    
    # Media Assets
    DataCategoryCreate(
        category_name="Media Content",
        description="User-uploaded media files and metadata",
        privacy_level=PrivacyLevel.CONFIDENTIAL,
        retention_days=2555,  # 7 years
        is_sensitive=False,
        requires_explicit_consent=False,
        can_be_anonymized=False,
        legal_basis="contract",
        purpose="Media asset management and storage",
        shared_with_third_parties=False
    ),
    
    # System Logs
    DataCategoryCreate(
        category_name="System Logs",
        description="Technical logs and audit trails",
        privacy_level=PrivacyLevel.INTERNAL,
        retention_days=365,  # 1 year
        is_sensitive=False,
        requires_explicit_consent=False,
        can_be_anonymized=True,
        legal_basis="legitimate_interest",
        purpose="Security monitoring and troubleshooting",
        shared_with_third_parties=False
    ),
    
    # Marketing Data
    DataCategoryCreate(
        category_name="Marketing Preferences",
        description="Marketing consent and communication preferences",
        privacy_level=PrivacyLevel.INTERNAL,
        retention_days=1095,  # 3 years
        is_sensitive=False,
        requires_explicit_consent=True,
        can_be_anonymized=False,
        legal_basis="consent",
        purpose="Marketing communications and preferences",
        shared_with_third_parties=False
    ),
    
    # IP and Location Data
    DataCategoryCreate(
        category_name="Location Data",
        description="IP addresses and geographic location",
        privacy_level=PrivacyLevel.CONFIDENTIAL,
        retention_days=180,  # 6 months
        is_sensitive=False,
        requires_explicit_consent=False,
        can_be_anonymized=True,
        legal_basis="legitimate_interest",
        purpose="Security, fraud prevention, and regional services",
        shared_with_third_parties=False
    )
]


# Default mappings for common MAMS tables
DEFAULT_MAPPINGS = {
    "users": [
        ("id", "User Identification", True, False, None),
        ("username", "User Identification", True, False, "pseudonymize"),
        ("email", "Contact Information", True, False, "mask_email"),
        ("password_hash", "Authentication Data", False, True, None),
        ("first_name", "Personal Details", True, False, "pseudonymize"),
        ("last_name", "Personal Details", True, False, "pseudonymize"),
        ("phone", "Contact Information", True, False, "mask_phone"),
        ("created_at", "System Logs", False, False, None),
        ("last_login", "Usage Analytics", False, False, None),
        ("is_active", "System Logs", False, False, None)
    ],
    
    "user_profiles": [
        ("user_id", "User Identification", True, False, None),
        ("bio", "Personal Details", True, False, "generalize"),
        ("avatar_url", "Personal Details", False, False, None),
        ("date_of_birth", "Personal Details", True, False, "generalize_date"),
        ("gender", "Personal Details", True, False, "generalize"),
        ("timezone", "Location Data", False, False, None),
        ("language", "Personal Details", False, False, None)
    ],
    
    "assets": [
        ("id", "Media Content", False, False, None),
        ("owner_id", "User Identification", True, False, None),
        ("file_path", "Media Content", False, False, None),
        ("metadata", "Media Content", False, False, None),
        ("created_at", "System Logs", False, False, None),
        ("updated_at", "System Logs", False, False, None)
    ],
    
    "audit_logs": [
        ("id", "System Logs", False, False, None),
        ("user_id", "User Identification", True, False, None),
        ("action", "System Logs", False, False, None),
        ("ip_address", "Location Data", True, False, "mask_ip"),
        ("user_agent", "System Logs", False, False, None),
        ("timestamp", "System Logs", False, False, None)
    ],
    
    "user_sessions": [
        ("id", "Authentication Data", False, False, None),
        ("user_id", "User Identification", True, False, None),
        ("token", "Authentication Data", False, True, None),
        ("ip_address", "Location Data", True, False, "mask_ip"),
        ("expires_at", "Authentication Data", False, False, None)
    ],
    
    "user_consents": [
        ("id", "Marketing Preferences", False, False, None),
        ("user_id", "User Identification", True, False, None),
        ("consent_type", "Marketing Preferences", False, False, None),
        ("consent_given", "Marketing Preferences", False, False, None),
        ("consent_date", "Marketing Preferences", False, False, None),
        ("ip_address", "Location Data", True, False, "mask_ip")
    ]
}


async def init_categories(service: DataClassificationService) -> dict:
    """Initialize default categories"""
    created_categories = {}
    
    for category_data in DEFAULT_CATEGORIES:
        try:
            category = await service.create_category(
                category_data,
                created_by="system_init"
            )
            created_categories[category.category_name] = category
            logger.info(f"Created category: {category.category_name}")
        except Exception as e:
            logger.warning(f"Failed to create category {category_data.category_name}: {e}")
            # Try to get existing category
            categories = await service.list_categories()
            for cat in categories:
                if cat.category_name == category_data.category_name:
                    created_categories[cat.category_name] = cat
                    break
    
    return created_categories


async def init_mappings(
    service: DataClassificationService,
    categories: dict
) -> int:
    """Initialize default mappings"""
    created_count = 0
    
    for table_name, columns in DEFAULT_MAPPINGS.items():
        for column_name, category_name, contains_pii, encrypted, anon_method in columns:
            if category_name not in categories:
                logger.warning(f"Category {category_name} not found, skipping mapping")
                continue
            
            try:
                mapping_data = DataMappingCreate(
                    table_name=table_name,
                    column_name=column_name,
                    category_id=categories[category_name].id,
                    field_description=f"{table_name}.{column_name}",
                    contains_pii=contains_pii,
                    encryption_required=encrypted,
                    anonymization_method=anon_method,
                    include_in_export=True
                )
                
                await service.create_mapping(
                    mapping_data,
                    created_by="system_init"
                )
                created_count += 1
                logger.info(f"Created mapping: {table_name}.{column_name} -> {category_name}")
            except Exception as e:
                logger.warning(f"Failed to create mapping {table_name}.{column_name}: {e}")
    
    return created_count


async def main():
    """Main initialization function"""
    # Create database engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        service = DataClassificationService(session)
        
        logger.info("Starting data classification initialization...")
        
        # Initialize categories
        categories = await init_categories(service)
        logger.info(f"Initialized {len(categories)} categories")
        
        # Initialize mappings
        mapping_count = await init_mappings(service, categories)
        logger.info(f"Initialized {mapping_count} mappings")
        
        # Generate initial report
        report = await service.generate_classification_report()
        logger.info(f"\nClassification Report:")
        logger.info(f"Total categories: {report.total_categories}")
        logger.info(f"Privacy levels: {report.categories_by_privacy_level}")
        logger.info(f"Sensitive categories: {len(report.sensitive_data_categories)}")
        logger.info(f"Third-party sharing: {len(report.third_party_sharing)}")
        
        if report.unmapped_tables:
            logger.warning(f"Unmapped tables: {report.unmapped_tables}")
        
        if report.compliance_gaps:
            logger.warning(f"Compliance gaps found: {len(report.compliance_gaps)}")
            for gap in report.compliance_gaps:
                logger.warning(f"  - {gap['type']}: {gap['description']}")
        
        logger.info("Data classification initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())