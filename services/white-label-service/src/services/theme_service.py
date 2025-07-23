"""
Theme management service for white-label customization
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
import uuid

from ..db.models import WhiteLabelTheme, ThemeTypeEnum
from ..models.schemas import ThemeCreate, ThemeUpdate, ThemeResponse
from ..core.exceptions import (
    ThemeNotFoundError, DuplicateResourceError, 
    ResourceLimitExceededError, ThemeValidationError
)
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class ThemeService:
    """Service for managing white-label themes"""
    
    async def create_theme(
        self,
        db: AsyncSession,
        tenant_id: str,
        theme_data: ThemeCreate
    ) -> WhiteLabelTheme:
        """Create a new theme"""
        
        # Check tenant theme limit
        theme_count = await self._get_tenant_theme_count(db, tenant_id)
        if theme_count >= settings.max_themes_per_tenant:
            raise ResourceLimitExceededError(
                f"Maximum themes ({settings.max_themes_per_tenant}) exceeded for tenant"
            )
        
        # Check for duplicate theme name
        existing_theme = await self._get_theme_by_name(db, tenant_id, theme_data.name)
        if existing_theme:
            raise DuplicateResourceError(f"Theme with name '{theme_data.name}' already exists")
        
        # Validate theme data
        self._validate_theme_data(theme_data)
        
        # Create theme
        theme = WhiteLabelTheme(
            tenant_id=tenant_id,
            name=theme_data.name,
            display_name=theme_data.display_name or theme_data.name,
            description=theme_data.description,
            theme_type=theme_data.theme_type,
            
            # Colors
            primary_color=theme_data.primary_color,
            secondary_color=theme_data.secondary_color,
            accent_color=theme_data.accent_color,
            background_color=theme_data.background_color,
            text_color=theme_data.text_color,
            link_color=theme_data.link_color,
            
            # Typography
            primary_font=theme_data.primary_font,
            secondary_font=theme_data.secondary_font,
            font_sizes=theme_data.font_sizes or {},
            font_weights=theme_data.font_weights or {},
            
            # Layout
            border_radius=theme_data.border_radius,
            spacing_unit=theme_data.spacing_unit,
            grid_columns=theme_data.grid_columns,
            breakpoints=theme_data.breakpoints or {},
            
            # Component Styles
            button_styles=theme_data.button_styles or {},
            card_styles=theme_data.card_styles or {},
            navigation_styles=theme_data.navigation_styles or {},
            form_styles=theme_data.form_styles or {},
            
            # Advanced
            custom_css=theme_data.custom_css,
            css_variables=theme_data.css_variables or {},
            component_overrides=theme_data.component_overrides or {},
            
            # Assets
            logo_url=str(theme_data.logo_url) if theme_data.logo_url else None,
            favicon_url=str(theme_data.favicon_url) if theme_data.favicon_url else None,
            background_image_url=str(theme_data.background_image_url) if theme_data.background_image_url else None,
            custom_images=theme_data.custom_images or [],
            
            # Dark Mode
            supports_dark_mode=theme_data.supports_dark_mode,
            dark_mode_colors=theme_data.dark_mode_colors or {},
            
            # Animation
            animation_settings=theme_data.animation_settings or {},
            transition_settings=theme_data.transition_settings or {},
        )
        
        # Set as default if this is the first theme
        if theme_count == 0:
            theme.is_default = True
        
        db.add(theme)
        await db.commit()
        await db.refresh(theme)
        
        logger.info(
            "theme_created",
            theme_id=str(theme.id),
            tenant_id=tenant_id,
            theme_name=theme.name,
            theme_type=theme.theme_type
        )
        
        return theme
    
    async def get_themes(
        self,
        db: AsyncSession,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        theme_type: Optional[ThemeTypeEnum] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[WhiteLabelTheme]:
        """Get themes for a tenant"""
        
        query = select(WhiteLabelTheme).where(WhiteLabelTheme.tenant_id == tenant_id)
        
        # Apply filters
        if theme_type:
            query = query.where(WhiteLabelTheme.theme_type == theme_type)
        
        if is_active is not None:
            query = query.where(WhiteLabelTheme.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    WhiteLabelTheme.name.ilike(search_term),
                    WhiteLabelTheme.display_name.ilike(search_term),
                    WhiteLabelTheme.description.ilike(search_term)
                )
            )
        
        # Apply pagination and ordering
        query = query.order_by(
            desc(WhiteLabelTheme.is_default),
            desc(WhiteLabelTheme.created_at)
        ).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_theme_by_id(
        self,
        db: AsyncSession,
        tenant_id: str,
        theme_id: str
    ) -> WhiteLabelTheme:
        """Get a specific theme by ID"""
        
        result = await db.execute(
            select(WhiteLabelTheme).where(
                and_(
                    WhiteLabelTheme.id == theme_id,
                    WhiteLabelTheme.tenant_id == tenant_id
                )
            )
        )
        theme = result.scalar_one_or_none()
        
        if not theme:
            raise ThemeNotFoundError(f"Theme {theme_id} not found")
        
        return theme
    
    async def get_default_theme(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Optional[WhiteLabelTheme]:
        """Get the default theme for a tenant"""
        
        result = await db.execute(
            select(WhiteLabelTheme).where(
                and_(
                    WhiteLabelTheme.tenant_id == tenant_id,
                    WhiteLabelTheme.is_default == True,
                    WhiteLabelTheme.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_theme(
        self,
        db: AsyncSession,
        tenant_id: str,
        theme_id: str,
        theme_data: ThemeUpdate
    ) -> WhiteLabelTheme:
        """Update a theme"""
        
        theme = await self.get_theme_by_id(db, tenant_id, theme_id)
        
        # Validate theme data
        if hasattr(theme_data, 'custom_css') and theme_data.custom_css:
            self._validate_custom_css(theme_data.custom_css)
        
        # Update fields
        update_data = theme_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(theme, field):
                if field in ['logo_url', 'favicon_url', 'background_image_url'] and value:
                    setattr(theme, field, str(value))
                else:
                    setattr(theme, field, value)
        
        await db.commit()
        await db.refresh(theme)
        
        logger.info(
            "theme_updated",
            theme_id=str(theme.id),
            tenant_id=tenant_id,
            updated_fields=list(update_data.keys())
        )
        
        return theme
    
    async def delete_theme(
        self,
        db: AsyncSession,
        tenant_id: str,
        theme_id: str
    ) -> bool:
        """Delete a theme"""
        
        theme = await self.get_theme_by_id(db, tenant_id, theme_id)
        
        # Check if theme is being used
        if theme.is_default:
            # Find another theme to set as default
            other_themes = await self.get_themes(
                db, 
                tenant_id, 
                is_active=True
            )
            other_themes = [t for t in other_themes if t.id != theme.id]
            
            if other_themes:
                # Set the first active theme as default
                other_themes[0].is_default = True
        
        await db.delete(theme)
        await db.commit()
        
        logger.info(
            "theme_deleted",
            theme_id=str(theme.id),
            tenant_id=tenant_id,
            theme_name=theme.name
        )
        
        return True
    
    async def set_default_theme(
        self,
        db: AsyncSession,
        tenant_id: str,
        theme_id: str
    ) -> WhiteLabelTheme:
        """Set a theme as the default for a tenant"""
        
        # Get the theme to set as default
        new_default = await self.get_theme_by_id(db, tenant_id, theme_id)
        
        # Unset current default
        await db.execute(
            select(WhiteLabelTheme).where(
                and_(
                    WhiteLabelTheme.tenant_id == tenant_id,
                    WhiteLabelTheme.is_default == True
                )
            ).update({"is_default": False})
        )
        
        # Set new default
        new_default.is_default = True
        await db.commit()
        await db.refresh(new_default)
        
        logger.info(
            "default_theme_changed",
            theme_id=str(theme_id),
            tenant_id=tenant_id
        )
        
        return new_default
    
    async def duplicate_theme(
        self,
        db: AsyncSession,
        tenant_id: str,
        theme_id: str,
        new_name: str
    ) -> WhiteLabelTheme:
        """Duplicate an existing theme"""
        
        # Get source theme
        source_theme = await self.get_theme_by_id(db, tenant_id, theme_id)
        
        # Check for duplicate name
        existing_theme = await self._get_theme_by_name(db, tenant_id, new_name)
        if existing_theme:
            raise DuplicateResourceError(f"Theme with name '{new_name}' already exists")
        
        # Create duplicate
        new_theme = WhiteLabelTheme(
            tenant_id=tenant_id,
            name=new_name,
            display_name=f"Copy of {source_theme.display_name}",
            description=source_theme.description,
            theme_type=source_theme.theme_type,
            
            # Copy all styling properties
            primary_color=source_theme.primary_color,
            secondary_color=source_theme.secondary_color,
            accent_color=source_theme.accent_color,
            background_color=source_theme.background_color,
            text_color=source_theme.text_color,
            link_color=source_theme.link_color,
            
            primary_font=source_theme.primary_font,
            secondary_font=source_theme.secondary_font,
            font_sizes=source_theme.font_sizes.copy() if source_theme.font_sizes else {},
            font_weights=source_theme.font_weights.copy() if source_theme.font_weights else {},
            
            border_radius=source_theme.border_radius,
            spacing_unit=source_theme.spacing_unit,
            grid_columns=source_theme.grid_columns,
            breakpoints=source_theme.breakpoints.copy() if source_theme.breakpoints else {},
            
            button_styles=source_theme.button_styles.copy() if source_theme.button_styles else {},
            card_styles=source_theme.card_styles.copy() if source_theme.card_styles else {},
            navigation_styles=source_theme.navigation_styles.copy() if source_theme.navigation_styles else {},
            form_styles=source_theme.form_styles.copy() if source_theme.form_styles else {},
            
            custom_css=source_theme.custom_css,
            css_variables=source_theme.css_variables.copy() if source_theme.css_variables else {},
            component_overrides=source_theme.component_overrides.copy() if source_theme.component_overrides else {},
            
            logo_url=source_theme.logo_url,
            favicon_url=source_theme.favicon_url,
            background_image_url=source_theme.background_image_url,
            custom_images=source_theme.custom_images.copy() if source_theme.custom_images else [],
            
            supports_dark_mode=source_theme.supports_dark_mode,
            dark_mode_colors=source_theme.dark_mode_colors.copy() if source_theme.dark_mode_colors else {},
            
            animation_settings=source_theme.animation_settings.copy() if source_theme.animation_settings else {},
            transition_settings=source_theme.transition_settings.copy() if source_theme.transition_settings else {},
        )
        
        db.add(new_theme)
        await db.commit()
        await db.refresh(new_theme)
        
        logger.info(
            "theme_duplicated",
            source_theme_id=str(theme_id),
            new_theme_id=str(new_theme.id),
            tenant_id=tenant_id,
            new_name=new_name
        )
        
        return new_theme
    
    async def generate_css(
        self,
        db: AsyncSession,
        tenant_id: str,
        theme_id: str
    ) -> str:
        """Generate CSS from theme configuration"""
        
        theme = await self.get_theme_by_id(db, tenant_id, theme_id)
        
        css_parts = []
        
        # CSS Variables
        if theme.css_variables or any([
            theme.primary_color, theme.secondary_color, theme.accent_color,
            theme.background_color, theme.text_color, theme.link_color
        ]):
            css_parts.append(":root {")
            
            # Color variables
            if theme.primary_color:
                css_parts.append(f"  --primary-color: {theme.primary_color};")
            if theme.secondary_color:
                css_parts.append(f"  --secondary-color: {theme.secondary_color};")
            if theme.accent_color:
                css_parts.append(f"  --accent-color: {theme.accent_color};")
            if theme.background_color:
                css_parts.append(f"  --background-color: {theme.background_color};")
            if theme.text_color:
                css_parts.append(f"  --text-color: {theme.text_color};")
            if theme.link_color:
                css_parts.append(f"  --link-color: {theme.link_color};")
            
            # Typography variables
            if theme.primary_font:
                css_parts.append(f"  --primary-font: {theme.primary_font};")
            if theme.secondary_font:
                css_parts.append(f"  --secondary-font: {theme.secondary_font};")
            
            # Layout variables
            if theme.border_radius:
                css_parts.append(f"  --border-radius: {theme.border_radius};")
            if theme.spacing_unit:
                css_parts.append(f"  --spacing-unit: {theme.spacing_unit};")
            
            # Custom CSS variables
            if theme.css_variables:
                for var_name, var_value in theme.css_variables.items():
                    css_parts.append(f"  --{var_name}: {var_value};")
            
            css_parts.append("}")
        
        # Font sizes
        if theme.font_sizes:
            for selector, size in theme.font_sizes.items():
                css_parts.append(f"{selector} {{ font-size: {size}; }}")
        
        # Custom CSS
        if theme.custom_css:
            css_parts.append(theme.custom_css)
        
        # Dark mode styles
        if theme.supports_dark_mode and theme.dark_mode_colors:
            css_parts.append("@media (prefers-color-scheme: dark) {")
            css_parts.append("  :root {")
            for var_name, var_value in theme.dark_mode_colors.items():
                css_parts.append(f"    --{var_name}: {var_value};")
            css_parts.append("  }")
            css_parts.append("}")
        
        return "\n".join(css_parts)
    
    async def get_theme_analytics(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get theme usage analytics"""
        
        from datetime import datetime, timedelta
        from ..db.models import WhiteLabelAnalytics
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get theme count
        theme_count_result = await db.execute(
            select(func.count(WhiteLabelTheme.id)).where(
                and_(
                    WhiteLabelTheme.tenant_id == tenant_id,
                    WhiteLabelTheme.is_active == True
                )
            )
        )
        total_themes = theme_count_result.scalar() or 0
        
        # Get theme usage
        usage_result = await db.execute(
            select(
                WhiteLabelAnalytics.resource_id,
                func.count(WhiteLabelAnalytics.id).label("usage_count")
            ).where(
                and_(
                    WhiteLabelAnalytics.tenant_id == tenant_id,
                    WhiteLabelAnalytics.resource_type == "theme",
                    WhiteLabelAnalytics.created_at >= start_date
                )
            ).group_by(WhiteLabelAnalytics.resource_id)
        )
        usage_data = {row.resource_id: row.usage_count for row in usage_result.all()}
        
        return {
            "total_themes": total_themes,
            "period_days": days,
            "usage_by_theme": usage_data,
            "total_usage": sum(usage_data.values())
        }
    
    # Private helper methods
    async def _get_tenant_theme_count(self, db: AsyncSession, tenant_id: str) -> int:
        """Get the number of themes for a tenant"""
        result = await db.execute(
            select(func.count(WhiteLabelTheme.id)).where(
                WhiteLabelTheme.tenant_id == tenant_id
            )
        )
        return result.scalar() or 0
    
    async def _get_theme_by_name(
        self, 
        db: AsyncSession, 
        tenant_id: str, 
        name: str
    ) -> Optional[WhiteLabelTheme]:
        """Get a theme by name within a tenant"""
        result = await db.execute(
            select(WhiteLabelTheme).where(
                and_(
                    WhiteLabelTheme.tenant_id == tenant_id,
                    WhiteLabelTheme.name == name
                )
            )
        )
        return result.scalar_one_or_none()
    
    def _validate_theme_data(self, theme_data: ThemeCreate) -> None:
        """Validate theme data"""
        errors = []
        
        # Validate CSS size
        if theme_data.custom_css and len(theme_data.custom_css) > settings.max_custom_css_size_kb * 1024:
            errors.append(f"Custom CSS exceeds maximum size of {settings.max_custom_css_size_kb}KB")
        
        # Validate colors
        color_fields = [
            'primary_color', 'secondary_color', 'accent_color',
            'background_color', 'text_color', 'link_color'
        ]
        for field in color_fields:
            color = getattr(theme_data, field, None)
            if color and not self._is_valid_hex_color(color):
                errors.append(f"Invalid hex color for {field}: {color}")
        
        # Validate dark mode colors
        if theme_data.dark_mode_colors:
            for var_name, color in theme_data.dark_mode_colors.items():
                if not self._is_valid_hex_color(color):
                    errors.append(f"Invalid hex color for dark mode variable {var_name}: {color}")
        
        if errors:
            raise ThemeValidationError(errors)
    
    def _validate_custom_css(self, css: str) -> None:
        """Validate custom CSS"""
        if len(css) > settings.max_custom_css_size_kb * 1024:
            raise ThemeValidationError([f"Custom CSS exceeds maximum size of {settings.max_custom_css_size_kb}KB"])
        
        # Basic CSS validation - check for potentially dangerous content
        dangerous_patterns = ['@import', 'javascript:', 'expression(', '<script']
        css_lower = css.lower()
        for pattern in dangerous_patterns:
            if pattern in css_lower:
                raise ThemeValidationError([f"Potentially dangerous CSS pattern detected: {pattern}"])
    
    def _is_valid_hex_color(self, color: str) -> bool:
        """Check if a string is a valid hex color"""
        if not color.startswith('#') or len(color) != 7:
            return False
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False