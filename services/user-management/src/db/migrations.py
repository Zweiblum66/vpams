"""
Database migration utilities for User Management Service

This module provides utilities for database migrations and initial data seeding.
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from passlib.context import CryptContext

from .base import engine, AsyncSessionLocal, Base
from .models import User, Role, Permission, UserProfile
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_tables():
    """Create all database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def drop_tables():
    """Drop all database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")


async def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """),
            {"table_name": table_name}
        )
        return result.scalar()


async def seed_permissions() -> List[Permission]:
    """Seed default permissions"""
    permissions_data = [
        # User management permissions
        {
            "name": "user:read",
            "display_name": "Read Users",
            "description": "View user information",
            "resource": "user",
            "action": "read",
            "category": "user_management",
            "scope": "global"
        },
        {
            "name": "user:write",
            "display_name": "Write Users",
            "description": "Create and update users",
            "resource": "user",
            "action": "write",
            "category": "user_management",
            "scope": "global"
        },
        {
            "name": "user:delete",
            "display_name": "Delete Users",
            "description": "Delete users",
            "resource": "user",
            "action": "delete",
            "category": "user_management",
            "scope": "global"
        },
        {
            "name": "user:admin",
            "display_name": "Administer Users",
            "description": "Full user administration",
            "resource": "user",
            "action": "admin",
            "category": "user_management",
            "scope": "global"
        },
        
        # Role management permissions
        {
            "name": "role:read",
            "display_name": "Read Roles",
            "description": "View role information",
            "resource": "role",
            "action": "read",
            "category": "role_management",
            "scope": "global"
        },
        {
            "name": "role:write",
            "display_name": "Write Roles",
            "description": "Create and update roles",
            "resource": "role",
            "action": "write",
            "category": "role_management",
            "scope": "global"
        },
        {
            "name": "role:delete",
            "display_name": "Delete Roles",
            "description": "Delete roles",
            "resource": "role",
            "action": "delete",
            "category": "role_management",
            "scope": "global"
        },
        {
            "name": "role:admin",
            "display_name": "Administer Roles",
            "description": "Full role administration",
            "resource": "role",
            "action": "admin",
            "category": "role_management",
            "scope": "global"
        },
        
        # Permission management
        {
            "name": "permission:read",
            "display_name": "Read Permissions",
            "description": "View permission information",
            "resource": "permission",
            "action": "read",
            "category": "permission_management",
            "scope": "global"
        },
        {
            "name": "permission:write",
            "display_name": "Write Permissions",
            "description": "Create and update permissions",
            "resource": "permission",
            "action": "write",
            "category": "permission_management",
            "scope": "global"
        },
        {
            "name": "permission:admin",
            "display_name": "Administer Permissions",
            "description": "Full permission administration",
            "resource": "permission",
            "action": "admin",
            "category": "permission_management",
            "scope": "global"
        },
        
        # Asset management permissions
        {
            "name": "asset:read",
            "display_name": "Read Assets",
            "description": "View asset information",
            "resource": "asset",
            "action": "read",
            "category": "asset_management",
            "scope": "global"
        },
        {
            "name": "asset:write",
            "display_name": "Write Assets",
            "description": "Create and update assets",
            "resource": "asset",
            "action": "write",
            "category": "asset_management",
            "scope": "global"
        },
        {
            "name": "asset:delete",
            "display_name": "Delete Assets",
            "description": "Delete assets",
            "resource": "asset",
            "action": "delete",
            "category": "asset_management",
            "scope": "global"
        },
        {
            "name": "asset:admin",
            "display_name": "Administer Assets",
            "description": "Full asset administration",
            "resource": "asset",
            "action": "admin",
            "category": "asset_management",
            "scope": "global"
        },
        
        # Project management permissions
        {
            "name": "project:read",
            "display_name": "Read Projects",
            "description": "View project information",
            "resource": "project",
            "action": "read",
            "category": "project_management",
            "scope": "global"
        },
        {
            "name": "project:write",
            "display_name": "Write Projects",
            "description": "Create and update projects",
            "resource": "project",
            "action": "write",
            "category": "project_management",
            "scope": "global"
        },
        {
            "name": "project:delete",
            "display_name": "Delete Projects",
            "description": "Delete projects",
            "resource": "project",
            "action": "delete",
            "category": "project_management",
            "scope": "global"
        },
        {
            "name": "project:admin",
            "display_name": "Administer Projects",
            "description": "Full project administration",
            "resource": "project",
            "action": "admin",
            "category": "project_management",
            "scope": "global"
        },
        
        # System permissions
        {
            "name": "system:read",
            "display_name": "Read System",
            "description": "View system information",
            "resource": "system",
            "action": "read",
            "category": "system",
            "scope": "global"
        },
        {
            "name": "system:admin",
            "display_name": "Administer System",
            "description": "Full system administration",
            "resource": "system",
            "action": "admin",
            "category": "system",
            "scope": "global"
        }
    ]
    
    async with AsyncSessionLocal() as session:
        permissions = []
        
        for perm_data in permissions_data:
            # Check if permission already exists
            existing = await session.execute(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            if existing.scalar_one_or_none():
                continue
                
            permission = Permission(
                id=uuid4(),
                name=perm_data["name"],
                display_name=perm_data["display_name"],
                description=perm_data["description"],
                resource=perm_data["resource"],
                action=perm_data["action"],
                category=perm_data["category"],
                scope=perm_data["scope"],
                is_system=True
            )
            session.add(permission)
            permissions.append(permission)
        
        await session.commit()
        logger.info(f"Seeded {len(permissions)} permissions")
        return permissions


async def seed_roles() -> List[Role]:
    """Seed default roles"""
    roles_data = [
        {
            "name": "super_admin",
            "display_name": "Super Administrator",
            "description": "Full system access with all permissions",
            "role_type": "system",
            "permissions": [
                "user:admin", "role:admin", "permission:admin",
                "asset:admin", "project:admin", "system:admin"
            ]
        },
        {
            "name": "admin",
            "display_name": "Administrator",
            "description": "Administrative access to most system functions",
            "role_type": "built-in",
            "permissions": [
                "user:read", "user:write", "user:delete",
                "role:read", "role:write",
                "asset:admin", "project:admin", "system:read"
            ]
        },
        {
            "name": "editor",
            "display_name": "Editor",
            "description": "Can edit content and manage projects",
            "role_type": "built-in",
            "permissions": [
                "user:read", "asset:read", "asset:write",
                "project:read", "project:write", "project:delete"
            ]
        },
        {
            "name": "contributor",
            "display_name": "Contributor",
            "description": "Can contribute content but limited editing",
            "role_type": "built-in",
            "permissions": [
                "user:read", "asset:read", "asset:write",
                "project:read", "project:write"
            ]
        },
        {
            "name": "viewer",
            "display_name": "Viewer",
            "description": "Read-only access to content",
            "role_type": "built-in",
            "permissions": [
                "user:read", "asset:read", "project:read"
            ]
        },
        {
            "name": "user",
            "display_name": "User",
            "description": "Basic user access",
            "role_type": "built-in",
            "permissions": [
                "asset:read", "project:read"
            ]
        }
    ]
    
    async with AsyncSessionLocal() as session:
        # Get all permissions for mapping
        permissions_result = await session.execute(select(Permission))
        permissions_by_name = {perm.name: perm for perm in permissions_result.scalars().all()}
        
        roles = []
        
        for role_data in roles_data:
            # Check if role already exists
            existing = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if existing.scalar_one_or_none():
                continue
                
            role = Role(
                id=uuid4(),
                name=role_data["name"],
                display_name=role_data["display_name"],
                description=role_data["description"],
                role_type=role_data["role_type"],
                is_system=role_data["role_type"] == "system"
            )
            
            # Add permissions to role
            for perm_name in role_data["permissions"]:
                if perm_name in permissions_by_name:
                    role.permissions.append(permissions_by_name[perm_name])
            
            session.add(role)
            roles.append(role)
        
        await session.commit()
        logger.info(f"Seeded {len(roles)} roles")
        return roles


async def create_super_admin() -> User:
    """Create default super admin user"""
    async with AsyncSessionLocal() as session:
        # Check if super admin already exists
        existing = await session.execute(
            select(User).where(User.email == "admin@mams.example.com")
        )
        if existing.scalar_one_or_none():
            logger.info("Super admin user already exists")
            return existing.scalar_one()
        
        # Get super admin role
        super_admin_role = await session.execute(
            select(Role).where(Role.name == "super_admin")
        )
        role = super_admin_role.scalar_one()
        
        # Create super admin user
        user = User(
            id=uuid4(),
            email="admin@mams.example.com",
            username="admin",
            password_hash=pwd_context.hash("admin123"),  # Default password
            first_name="System",
            last_name="Administrator",
            display_name="System Administrator",
            is_active=True,
            is_verified=True,
            is_superuser=True,
            email_verified_at=datetime.now(timezone.utc)
        )
        
        # Add super admin role
        user.roles.append(role)
        
        session.add(user)
        await session.commit()
        
        # Create user profile
        profile = UserProfile(
            id=uuid4(),
            user_id=user.id,
            department="IT",
            job_title="System Administrator",
            organization="MAMS",
            timezone="UTC",
            language="en",
            preferences={
                "theme": "dark",
                "notifications": {
                    "email": True,
                    "in_app": True
                }
            }
        )
        
        session.add(profile)
        await session.commit()
        
        logger.info("Created super admin user: admin@mams.example.com")
        return user


async def seed_database():
    """Seed database with initial data"""
    logger.info("Starting database seeding...")
    
    try:
        # Create tables
        await create_tables()
        
        # Seed permissions
        await seed_permissions()
        
        # Seed roles
        await seed_roles()
        
        # Create super admin
        await create_super_admin()
        
        logger.info("Database seeding completed successfully")
        
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise


async def reset_database():
    """Reset database (drop and recreate with seed data)"""
    logger.warning("Resetting database...")
    
    try:
        # Drop tables
        await drop_tables()
        
        # Seed database
        await seed_database()
        
        logger.info("Database reset completed successfully")
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise


async def check_database_health() -> bool:
    """Check database health and connectivity"""
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connectivity
            await session.execute(text("SELECT 1"))
            
            # Check if core tables exist
            tables = ["users", "roles", "permissions", "user_profiles"]
            for table in tables:
                if not await check_table_exists(table):
                    logger.error(f"Table {table} does not exist")
                    return False
            
            # Check if basic data exists
            user_count = await session.execute(text("SELECT COUNT(*) FROM users"))
            role_count = await session.execute(text("SELECT COUNT(*) FROM roles"))
            perm_count = await session.execute(text("SELECT COUNT(*) FROM permissions"))
            
            if user_count.scalar() == 0 or role_count.scalar() == 0 or perm_count.scalar() == 0:
                logger.warning("Database appears to be empty")
                return False
            
            logger.info("Database health check passed")
            return True
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


if __name__ == "__main__":
    # CLI interface for migrations
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration utility")
    parser.add_argument("command", choices=["create", "seed", "reset", "health"])
    args = parser.parse_args()
    
    async def main():
        if args.command == "create":
            await create_tables()
        elif args.command == "seed":
            await seed_database()
        elif args.command == "reset":
            await reset_database()
        elif args.command == "health":
            healthy = await check_database_health()
            sys.exit(0 if healthy else 1)
    
    asyncio.run(main())