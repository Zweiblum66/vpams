"""
Branding management service for white-label customization
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
import uuid
from datetime import datetime

from ..db.models import WhiteLabelBranding, WhiteLabelTheme, BrandingStatusEnum
from ..models.schemas import BrandingCreate, BrandingUpdate, BrandingResponse
from ..core.exceptions import (
    BrandingNotFoundError, ThemeNotFoundError, 
    InvalidConfigurationError, DuplicateResourceError
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class BrandingService:
    """Service for managing white-label branding configuration"""
    
    async def create_branding(
        self,
        db: AsyncSession,
        tenant_id: str,
        branding_data: BrandingCreate
    ) -> WhiteLabelBranding:
        """Create branding configuration for a tenant"""
        
        # Check if branding already exists for tenant
        existing_branding = await self.get_branding_by_tenant(db, tenant_id)
        if existing_branding:
            raise DuplicateResourceError(f"Branding configuration already exists for tenant {tenant_id}")
        
        # Validate theme if provided
        theme = None
        if branding_data.theme_id:
            theme = await self._get_theme_by_id(db, tenant_id, branding_data.theme_id)
            if not theme:
                raise ThemeNotFoundError(f"Theme {branding_data.theme_id} not found")
        
        # Create branding configuration
        branding = WhiteLabelBranding(
            tenant_id=tenant_id,
            theme_id=branding_data.theme_id,
            status=BrandingStatusEnum.DRAFT,
            
            # Company information
            company_name=branding_data.company_name,
            company_tagline=branding_data.company_tagline,
            company_description=branding_data.company_description,
            company_website=str(branding_data.company_website) if branding_data.company_website else None,
            
            # Contact information
            contact_email=branding_data.contact_email,
            support_email=branding_data.support_email,
            phone_number=branding_data.phone_number,
            address=branding_data.address.model_dump() if branding_data.address else {},
            
            # Legal information
            terms_of_service_url=str(branding_data.terms_of_service_url) if branding_data.terms_of_service_url else None,
            privacy_policy_url=str(branding_data.privacy_policy_url) if branding_data.privacy_policy_url else None,
            copyright_text=branding_data.copyright_text,
            legal_entity_name=branding_data.legal_entity_name,
            
            # Social media
            social_media_links=branding_data.social_media_links or {},
            
            # Platform configuration
            platform_name=branding_data.platform_name,
            welcome_message=branding_data.welcome_message,
            login_message=branding_data.login_message,
            footer_text=branding_data.footer_text,
            
            # Feature configuration
            feature_visibility=branding_data.feature_visibility or {},
            navigation_menu=branding_data.navigation_menu or [],
            
            # Email configuration
            from_email=branding_data.from_email,
            from_name=branding_data.from_name,
            reply_to_email=branding_data.reply_to_email,
            email_signature=branding_data.email_signature,
            
            # API branding
            api_documentation_title=branding_data.api_documentation_title,
            api_description=branding_data.api_description,
            api_contact_info=branding_data.api_contact_info or {},
        )
        
        db.add(branding)
        await db.commit()
        await db.refresh(branding)
        
        logger.info(
            "branding_created",
            branding_id=str(branding.id),
            tenant_id=tenant_id,
            company_name=branding.company_name
        )
        
        return branding
    
    async def get_branding_by_tenant(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Optional[WhiteLabelBranding]:
        """Get branding configuration by tenant ID"""
        
        result = await db.execute(
            select(WhiteLabelBranding)
            .options(selectinload(WhiteLabelBranding.theme))
            .where(WhiteLabelBranding.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def get_branding_by_id(
        self,
        db: AsyncSession,
        branding_id: str
    ) -> WhiteLabelBranding:
        """Get branding configuration by ID"""
        
        result = await db.execute(
            select(WhiteLabelBranding)
            .options(selectinload(WhiteLabelBranding.theme))
            .where(WhiteLabelBranding.id == branding_id)
        )
        branding = result.scalar_one_or_none()
        
        if not branding:
            raise BrandingNotFoundError(f"Branding configuration {branding_id} not found")
        
        return branding
    
    async def update_branding(
        self,
        db: AsyncSession,
        tenant_id: str,
        branding_data: BrandingUpdate
    ) -> WhiteLabelBranding:
        """Update branding configuration"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding:
            raise BrandingNotFoundError(f"Branding configuration for tenant {tenant_id} not found")
        
        # Validate theme if provided
        if branding_data.theme_id:
            theme = await self._get_theme_by_id(db, tenant_id, branding_data.theme_id)
            if not theme:
                raise ThemeNotFoundError(f"Theme {branding_data.theme_id} not found")
        
        # Update fields
        update_data = branding_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(branding, field):
                if field in ['company_website', 'terms_of_service_url', 'privacy_policy_url'] and value:
                    setattr(branding, field, str(value))
                elif field == 'address' and value:
                    setattr(branding, field, value.model_dump() if hasattr(value, 'model_dump') else value)
                else:
                    setattr(branding, field, value)
        
        await db.commit()
        await db.refresh(branding)
        
        logger.info(
            "branding_updated",
            branding_id=str(branding.id),
            tenant_id=tenant_id,
            updated_fields=list(update_data.keys())
        )
        
        return branding
    
    async def activate_branding(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> WhiteLabelBranding:
        """Activate branding configuration"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding:
            raise BrandingNotFoundError(f"Branding configuration for tenant {tenant_id} not found")
        
        # Validate required fields
        self._validate_branding_for_activation(branding)
        
        branding.status = BrandingStatusEnum.ACTIVE
        branding.activated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(branding)
        
        logger.info(
            "branding_activated",
            branding_id=str(branding.id),
            tenant_id=tenant_id
        )
        
        return branding
    
    async def deactivate_branding(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> WhiteLabelBranding:
        """Deactivate branding configuration"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding:
            raise BrandingNotFoundError(f"Branding configuration for tenant {tenant_id} not found")
        
        branding.status = BrandingStatusEnum.INACTIVE
        
        await db.commit()
        await db.refresh(branding)
        
        logger.info(
            "branding_deactivated",
            branding_id=str(branding.id),
            tenant_id=tenant_id
        )
        
        return branding
    
    async def delete_branding(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> bool:
        """Delete branding configuration"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding:
            raise BrandingNotFoundError(f"Branding configuration for tenant {tenant_id} not found")
        
        await db.delete(branding)
        await db.commit()
        
        logger.info(
            "branding_deleted",
            branding_id=str(branding.id),
            tenant_id=tenant_id
        )
        
        return True
    
    async def get_public_branding(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get public branding information (safe for client-side use)"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding or branding.status != BrandingStatusEnum.ACTIVE:
            return {}
        
        # Return only public information
        public_branding = {
            "company_name": branding.company_name,
            "company_tagline": branding.company_tagline,
            "company_website": branding.company_website,
            "platform_name": branding.platform_name,
            "welcome_message": branding.welcome_message,
            "login_message": branding.login_message,
            "footer_text": branding.footer_text,
            "copyright_text": branding.copyright_text,
            "social_media_links": branding.social_media_links,
            "feature_visibility": branding.feature_visibility,
            "navigation_menu": branding.navigation_menu,
        }
        
        # Include theme information if available
        if branding.theme:
            public_branding["theme"] = {
                "id": str(branding.theme.id),
                "name": branding.theme.name,
                "display_name": branding.theme.display_name,
                "primary_color": branding.theme.primary_color,
                "secondary_color": branding.theme.secondary_color,
                "accent_color": branding.theme.accent_color,
                "logo_url": branding.theme.logo_url,
                "favicon_url": branding.theme.favicon_url,
            }
        
        return public_branding
    
    async def get_email_branding(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get email branding configuration"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding:
            return {}
        
        return {
            "from_email": branding.from_email,
            "from_name": branding.from_name,
            "reply_to_email": branding.reply_to_email,
            "email_signature": branding.email_signature,
            "company_name": branding.company_name,
            "company_website": branding.company_website,
            "support_email": branding.support_email,
        }
    
    async def get_api_branding(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get API documentation branding"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding:
            return {}
        
        return {
            "title": branding.api_documentation_title or f"{branding.company_name} API",
            "description": branding.api_description or f"API documentation for {branding.company_name}",
            "contact": branding.api_contact_info or {},
            "company_name": branding.company_name,
            "company_website": branding.company_website,
            "terms_of_service": branding.terms_of_service_url,
        }
    
    async def validate_branding_configuration(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Validate branding configuration completeness"""
        
        branding = await self.get_branding_by_tenant(db, tenant_id)
        if not branding:
            return {
                "is_valid": False,
                "errors": ["No branding configuration found"],
                "warnings": [],
                "completion_percentage": 0
            }
        
        errors = []
        warnings = []
        completed_fields = 0
        total_fields = 0
        
        # Required fields
        required_fields = [
            ("company_name", "Company name is required"),
            ("contact_email", "Contact email is required"),
        ]
        
        for field, error_message in required_fields:
            total_fields += 1
            if getattr(branding, field):
                completed_fields += 1
            else:
                errors.append(error_message)
        
        # Recommended fields
        recommended_fields = [
            ("company_tagline", "Company tagline is recommended"),
            ("company_description", "Company description is recommended"),
            ("company_website", "Company website is recommended"),
            ("support_email", "Support email is recommended"),
            ("privacy_policy_url", "Privacy policy URL is recommended"),
            ("terms_of_service_url", "Terms of service URL is recommended"),
        ]
        
        for field, warning_message in recommended_fields:
            total_fields += 1
            if getattr(branding, field):
                completed_fields += 1
            else:
                warnings.append(warning_message)
        
        # Theme validation
        if branding.theme_id:
            total_fields += 1
            try:
                theme = await self._get_theme_by_id(db, tenant_id, branding.theme_id)
                if theme:
                    completed_fields += 1
                else:
                    errors.append("Associated theme not found")
            except:
                errors.append("Associated theme not found")
        else:
            warnings.append("No theme selected")
        
        completion_percentage = (completed_fields / total_fields * 100) if total_fields > 0 else 0
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "completion_percentage": round(completion_percentage, 2),
            "completed_fields": completed_fields,
            "total_fields": total_fields
        }
    
    # Private helper methods
    async def _get_theme_by_id(
        self, 
        db: AsyncSession, 
        tenant_id: str, 
        theme_id: str
    ) -> Optional[WhiteLabelTheme]:
        """Get a theme by ID for a specific tenant"""
        result = await db.execute(
            select(WhiteLabelTheme).where(
                and_(
                    WhiteLabelTheme.id == theme_id,
                    WhiteLabelTheme.tenant_id == tenant_id,
                    WhiteLabelTheme.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    def _validate_branding_for_activation(self, branding: WhiteLabelBranding) -> None:
        """Validate that branding has required fields for activation"""
        errors = []
        
        if not branding.company_name:
            errors.append("Company name is required for activation")
        
        if not branding.contact_email:
            errors.append("Contact email is required for activation")
        
        if errors:
            raise InvalidConfigurationError("; ".join(errors))