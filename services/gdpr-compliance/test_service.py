"""Quick test to verify GDPR Compliance Service can start"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Core imports
        from core.config import settings
        print("✓ Config imported successfully")
        
        # Database imports
        from db.base import Base, engine
        from db.models import UserConsent, DataRequest
        print("✓ Database models imported successfully")
        
        # Service imports
        from services.data_export_service import DataExportService
        from services.data_deletion_service import DataDeletionService
        from services.audit_service import AuditService
        print("✓ Services imported successfully")
        
        # API imports
        from api.routes import router
        print("✓ API routes imported successfully")
        
        # Main app
        from main import app
        print("✓ FastAPI app imported successfully")
        
        print("\n✅ All imports successful!")
        
        # Print some config info
        print(f"\nConfiguration:")
        print(f"  Service Name: {settings.service_name}")
        print(f"  Port: {settings.port}")
        print(f"  Debug Mode: {settings.debug}")
        print(f"  Database URL: {settings.database_url.split('@')[0]}@...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_models():
    """Test database model creation"""
    try:
        print("\nTesting database models...")
        
        from db.base import Base, engine
        from sqlalchemy import inspect
        
        # Create an inspector
        async with engine.connect() as conn:
            def inspect_tables(connection):
                inspector = inspect(connection)
                return inspector.get_table_names()
            
            existing_tables = await conn.run_sync(inspect_tables)
            
            print(f"Existing tables: {existing_tables}")
            
            # Get all model tables
            model_tables = list(Base.metadata.tables.keys())
            print(f"Model tables: {model_tables}")
            
            print("✓ Database models defined successfully")
            
        return True
        
    except Exception as e:
        print(f"\n❌ Database test failed: {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("GDPR Compliance Service - Quick Test")
    print("=" * 50)
    
    # Test imports
    if not await test_imports():
        return
    
    # Test database models
    await test_database_models()
    
    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(main())