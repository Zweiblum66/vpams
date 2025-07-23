"""
User Service

Business logic for user management operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import logging

from db.models import User, UserProfile, Role, Permission
from models.schemas import (
    UserRegistrationRequest,
    UserUpdateRequest,
    PaginationParams,
    SortParams,
    FilterParams
)
from core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user management operations"""
    
    async def get_user_by_id(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        try:
            result = await db.execute(
                select(User)
                .options(selectinload(User.profile), selectinload(User.roles))
                .where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address"""
        try:
            result = await db.execute(
                select(User)
                .options(selectinload(User.profile), selectinload(User.roles))
                .where(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            result = await db.execute(
                select(User)
                .options(selectinload(User.profile), selectinload(User.roles))
                .where(User.username == username)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    async def get_users(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        sort: SortParams,
        filters: FilterParams
    ) -> tuple[List[User], int]:
        """Get paginated list of users with filtering and sorting"""
        try:
            # Build base query
            query = select(User).options(
                selectinload(User.profile),
                selectinload(User.roles)
            )
            
            # Apply filters
            conditions = []
            
            if filters.is_active is not None:
                conditions.append(User.is_active == filters.is_active)
            
            if filters.is_verified is not None:
                conditions.append(User.is_verified == filters.is_verified)
            
            if filters.department:
                query = query.join(UserProfile).where(
                    UserProfile.department.ilike(f"%{filters.department}%")
                )
            
            if filters.organization:
                query = query.join(UserProfile).where(
                    UserProfile.organization.ilike(f"%{filters.organization}%")
                )
            
            if filters.created_after:
                conditions.append(User.created_at >= filters.created_after)
            
            if filters.created_before:
                conditions.append(User.created_at <= filters.created_before)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply sorting
            if sort.sort == "email":
                order_col = User.email
            elif sort.sort == "username":
                order_col = User.username
            elif sort.sort == "first_name":
                order_col = User.first_name
            elif sort.sort == "last_name":
                order_col = User.last_name
            elif sort.sort == "created_at":
                order_col = User.created_at
            else:
                order_col = User.created_at
            
            if sort.order == "desc":
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(order_col)
            
            # Get total count
            count_query = select(func.count(User.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply pagination
            query = query.offset(pagination.offset).limit(pagination.limit)
            
            # Execute query
            result = await db.execute(query)
            users = result.scalars().all()
            
            return list(users), total_count
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return [], 0
    
    async def create_user(
        self,
        db: AsyncSession,
        user_data: UserRegistrationRequest,
        is_superuser: bool = False
    ) -> User:
        """Create a new user"""
        try:
            # Create user
            user = User(
                email=user_data.email,
                username=user_data.username,
                password_hash=get_password_hash(user_data.password),
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                display_name=f"{user_data.first_name} {user_data.last_name}",
                is_active=True,
                is_verified=False,
                is_superuser=is_superuser,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Create profile
            profile = UserProfile(
                user_id=user.id,
                phone=user_data.phone,
                department=user_data.department,
                job_title=user_data.job_title,
                organization=user_data.organization,
                timezone=user_data.timezone or "UTC",
                language=user_data.language or "en",
                preferences={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Add to session
            db.add(user)
            db.add(profile)
            
            # Assign default role
            default_role = await self.get_default_role(db)
            if default_role:
                user.roles.append(default_role)
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"User created successfully: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await db.rollback()
            raise
    
    async def update_user(
        self,
        db: AsyncSession,
        user: User,
        user_data: UserUpdateRequest
    ) -> User:
        """Update user information"""
        try:
            # Update user fields
            if user_data.first_name is not None:
                user.first_name = user_data.first_name
            if user_data.last_name is not None:
                user.last_name = user_data.last_name
            if user_data.display_name is not None:
                user.display_name = user_data.display_name
            if user_data.username is not None:
                user.username = user_data.username
            
            # Update profile
            await db.refresh(user, ["profile"])
            profile = user.profile
            
            if user_data.phone is not None:
                profile.phone = user_data.phone
            if user_data.department is not None:
                profile.department = user_data.department
            if user_data.job_title is not None:
                profile.job_title = user_data.job_title
            if user_data.organization is not None:
                profile.organization = user_data.organization
            if user_data.location is not None:
                profile.location = user_data.location
            if user_data.timezone is not None:
                profile.timezone = user_data.timezone
            if user_data.language is not None:
                profile.language = user_data.language
            if user_data.bio is not None:
                profile.bio = user_data.bio
            if user_data.website is not None:
                profile.website = user_data.website
            if user_data.preferences is not None:
                profile.preferences = user_data.preferences
            
            # Update timestamps
            user.updated_at = datetime.now(timezone.utc)
            profile.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"User updated successfully: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            await db.rollback()
            raise
    
    async def delete_user(self, db: AsyncSession, user_id: UUID) -> bool:
        """Delete (deactivate) user"""
        try:
            user = await self.get_user_by_id(db, user_id)
            if not user:
                return False
            
            # Soft delete - deactivate user
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"User deleted successfully: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            await db.rollback()
            return False
    
    async def activate_user(self, db: AsyncSession, user_id: UUID) -> bool:
        """Activate user account"""
        try:
            user = await self.get_user_by_id(db, user_id)
            if not user:
                return False
            
            user.is_active = True
            user.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"User activated successfully: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error activating user: {e}")
            await db.rollback()
            return False
    
    async def verify_user_email(self, db: AsyncSession, user_id: UUID) -> bool:
        """Verify user email"""
        try:
            user = await self.get_user_by_id(db, user_id)
            if not user:
                return False
            
            user.is_verified = True
            user.email_verified_at = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Email verified successfully: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            await db.rollback()
            return False
    
    async def change_password(
        self,
        db: AsyncSession,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password"""
        try:
            # Verify current password
            if not verify_password(current_password, user.password_hash):
                return False
            
            # Update password
            user.password_hash = get_password_hash(new_password)
            user.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Password changed successfully: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            await db.rollback()
            return False
    
    async def get_default_role(self, db: AsyncSession) -> Optional[Role]:
        """Get default role for new users"""
        try:
            result = await db.execute(
                select(Role).where(Role.name == "user")
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting default role: {e}")
            return None
    
    async def assign_role(self, db: AsyncSession, user_id: UUID, role_name: str) -> bool:
        """Assign role to user"""
        try:
            user = await self.get_user_by_id(db, user_id)
            if not user:
                return False
            
            # Get role
            result = await db.execute(
                select(Role).where(Role.name == role_name)
            )
            role = result.scalar_one_or_none()
            if not role:
                return False
            
            # Check if user already has role
            await db.refresh(user, ["roles"])
            if role in user.roles:
                return True
            
            # Add role to user
            user.roles.append(role)
            user.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            logger.info(f"Role '{role_name}' assigned to user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            await db.rollback()
            return False
    
    async def remove_role(self, db: AsyncSession, user_id: UUID, role_name: str) -> bool:
        """Remove role from user"""
        try:
            user = await self.get_user_by_id(db, user_id)
            if not user:
                return False
            
            # Get role
            result = await db.execute(
                select(Role).where(Role.name == role_name)
            )
            role = result.scalar_one_or_none()
            if not role:
                return False
            
            # Remove role from user
            await db.refresh(user, ["roles"])
            if role in user.roles:
                user.roles.remove(role)
                user.updated_at = datetime.now(timezone.utc)
                await db.commit()
            
            logger.info(f"Role '{role_name}' removed from user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing role: {e}")
            await db.rollback()
            return False
    
    async def search_users(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10
    ) -> List[User]:
        """Search users by name, email, or username"""
        try:
            search_query = select(User).options(
                selectinload(User.profile),
                selectinload(User.roles)
            ).where(
                or_(
                    User.email.ilike(f"%{query}%"),
                    User.username.ilike(f"%{query}%"),
                    User.first_name.ilike(f"%{query}%"),
                    User.last_name.ilike(f"%{query}%"),
                    User.display_name.ilike(f"%{query}%")
                )
            ).limit(limit)
            
            result = await db.execute(search_query)
            users = result.scalars().all()
            
            return list(users)
            
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []