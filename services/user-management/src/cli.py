#!/usr/bin/env python3
"""
CLI utility for User Management Service

Provides command-line interface for database operations and testing.
"""

import asyncio
import sys
import argparse
import logging
from typing import Optional

from db.base import init_db, close_db, check_db_health
from db.migrations import (
    create_tables, 
    seed_database, 
    reset_database, 
    check_database_health
)
from core.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def cmd_init():
    """Initialize database tables"""
    logger.info("Initializing database tables...")
    try:
        await init_db()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


async def cmd_seed():
    """Seed database with initial data"""
    logger.info("Seeding database with initial data...")
    try:
        await seed_database()
        logger.info("Database seeded successfully")
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        sys.exit(1)


async def cmd_reset():
    """Reset database (drop and recreate with seed data)"""
    logger.warning("This will reset the database and delete all data!")
    response = input("Are you sure you want to continue? (y/N): ")
    
    if response.lower() != 'y':
        logger.info("Database reset cancelled")
        return
    
    logger.info("Resetting database...")
    try:
        await reset_database()
        logger.info("Database reset successfully")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        sys.exit(1)


async def cmd_health():
    """Check database health"""
    logger.info("Checking database health...")
    try:
        healthy = await check_database_health()
        if healthy:
            logger.info("Database is healthy")
        else:
            logger.error("Database is unhealthy")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        sys.exit(1)


async def cmd_test_schema():
    """Test database schema by creating sample data"""
    logger.info("Testing database schema...")
    
    try:
        from db.models import User, Role, Permission, UserProfile
        from db.base import AsyncSessionLocal
        from uuid import uuid4
        from datetime import datetime, timezone
        
        async with AsyncSessionLocal() as session:
            # Create test permission
            permission = Permission(
                id=uuid4(),
                name="test:read",
                display_name="Test Read",
                description="Test permission",
                resource="test",
                action="read",
                category="testing"
            )
            
            # Create test role
            role = Role(
                id=uuid4(),
                name="test_role",
                display_name="Test Role",
                description="Test role",
                role_type="custom"
            )
            role.permissions.append(permission)
            
            # Create test user
            user = User(
                id=uuid4(),
                email="test@example.com",
                username="testuser",
                password_hash="hashed_password",
                first_name="Test",
                last_name="User",
                display_name="Test User",
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.now(timezone.utc)
            )
            user.roles.append(role)
            
            # Create test profile
            profile = UserProfile(
                id=uuid4(),
                user_id=user.id,
                department="Engineering",
                job_title="Developer",
                timezone="UTC",
                language="en",
                preferences={"theme": "dark"}
            )
            
            # Save all objects
            session.add_all([permission, role, user, profile])
            await session.commit()
            
            logger.info("Test data created successfully")
            
            # Verify relationships
            await session.refresh(user, ["roles", "profile"])
            await session.refresh(role, ["permissions"])
            
            assert len(user.roles) == 1
            assert user.roles[0].name == "test_role"
            assert len(user.roles[0].permissions) == 1
            assert user.roles[0].permissions[0].name == "test:read"
            assert user.profile.department == "Engineering"
            
            logger.info("Schema relationships verified successfully")
            
    except Exception as e:
        logger.error(f"Schema test failed: {e}")
        sys.exit(1)


async def cmd_status():
    """Show database status and statistics"""
    logger.info("Getting database status...")
    
    try:
        from db.base import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            # Get table counts
            user_count = await session.execute(text("SELECT COUNT(*) FROM users"))
            role_count = await session.execute(text("SELECT COUNT(*) FROM roles"))
            permission_count = await session.execute(text("SELECT COUNT(*) FROM permissions"))
            profile_count = await session.execute(text("SELECT COUNT(*) FROM user_profiles"))
            session_count = await session.execute(text("SELECT COUNT(*) FROM user_sessions"))
            
            print("\n=== Database Status ===")
            print(f"Users: {user_count.scalar()}")
            print(f"Roles: {role_count.scalar()}")
            print(f"Permissions: {permission_count.scalar()}")
            print(f"User Profiles: {profile_count.scalar()}")
            print(f"User Sessions: {session_count.scalar()}")
            
            # Get recent activity
            recent_users = await session.execute(
                text("SELECT email, created_at FROM users ORDER BY created_at DESC LIMIT 5")
            )
            
            print("\n=== Recent Users ===")
            for user in recent_users:
                print(f"- {user.email} (created: {user.created_at})")
            
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="User Management Service CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Database commands
    subparsers.add_parser("init", help="Initialize database tables")
    subparsers.add_parser("seed", help="Seed database with initial data")
    subparsers.add_parser("reset", help="Reset database (WARNING: deletes all data)")
    subparsers.add_parser("health", help="Check database health")
    subparsers.add_parser("test-schema", help="Test database schema")
    subparsers.add_parser("status", help="Show database status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Command mapping
    commands = {
        "init": cmd_init,
        "seed": cmd_seed,
        "reset": cmd_reset,
        "health": cmd_health,
        "test-schema": cmd_test_schema,
        "status": cmd_status
    }
    
    if args.command in commands:
        try:
            asyncio.run(commands[args.command]())
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Command failed: {e}")
            sys.exit(1)
    else:
        logger.error(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()