"""
Shared test utilities for MAMS services
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import jwt
from faker import Faker

fake = Faker()


class TestDataGenerator:
    """Generate test data for various entities"""
    
    @staticmethod
    def create_user(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate test user data"""
        user_data = {
            "id": str(uuid.uuid4()),
            "email": fake.email(),
            "username": fake.user_name(),
            "full_name": fake.name(),
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        if overrides:
            user_data.update(overrides)
        return user_data
    
    @staticmethod
    def create_asset(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate test asset data"""
        asset_data = {
            "id": str(uuid.uuid4()),
            "name": fake.file_name(extension="mp4"),
            "file_path": f"/storage/{fake.uuid4()}.mp4",
            "file_size": fake.random_int(min=1000000, max=1000000000),
            "mime_type": "video/mp4",
            "duration": fake.random_int(min=60, max=3600),
            "width": 1920,
            "height": 1080,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "tags": [fake.word() for _ in range(3)],
            "metadata": {
                "codec": "h264",
                "bitrate": "5000k",
                "fps": 30,
            }
        }
        if overrides:
            asset_data.update(overrides)
        return asset_data
    
    @staticmethod
    def create_project(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate test project data"""
        project_data = {
            "id": str(uuid.uuid4()),
            "name": fake.catch_phrase(),
            "description": fake.text(max_nb_chars=200),
            "type": "project",
            "owner_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "settings": {
                "frame_rate": 30,
                "resolution": "1920x1080",
                "aspect_ratio": "16:9",
            }
        }
        if overrides:
            project_data.update(overrides)
        return project_data
    
    @staticmethod
    def create_workflow(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate test workflow data"""
        workflow_data = {
            "id": str(uuid.uuid4()),
            "name": f"Test Workflow {fake.word()}",
            "description": fake.text(max_nb_chars=100),
            "type": "ingest",
            "status": "active",
            "steps": [
                {
                    "id": "validate",
                    "type": "validation",
                    "config": {"check_format": True}
                },
                {
                    "id": "transcode",
                    "type": "transcode",
                    "config": {"preset": "proxy"}
                }
            ],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        if overrides:
            workflow_data.update(overrides)
        return workflow_data


class AuthTestUtils:
    """Authentication utilities for testing"""
    
    @staticmethod
    def create_test_token(
        user_id: str,
        email: str,
        roles: list = None,
        expires_delta: timedelta = None
    ) -> str:
        """Create a test JWT token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "roles": roles or ["user"],
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        # Use a test secret key
        secret_key = "test-secret-key-do-not-use-in-production"
        return jwt.encode(to_encode, secret_key, algorithm="HS256")
    
    @staticmethod
    def get_auth_headers(token: str) -> Dict[str, str]:
        """Get authorization headers with token"""
        return {"Authorization": f"Bearer {token}"}


class DatabaseTestUtils:
    """Database utilities for testing"""
    
    @staticmethod
    async def clean_database(db_session):
        """Clean all data from test database"""
        # This would be implemented based on your specific database setup
        pass
    
    @staticmethod
    async def seed_test_data(db_session, data_type: str, count: int = 5):
        """Seed database with test data"""
        # This would be implemented based on your specific models
        pass


class MockExternalServices:
    """Mock external service calls for testing"""
    
    @staticmethod
    def mock_storage_service():
        """Mock storage service responses"""
        return {
            "upload_file": lambda *args, **kwargs: {
                "file_id": str(uuid.uuid4()),
                "url": f"https://storage.test/{uuid.uuid4()}",
                "size": 1024000
            },
            "delete_file": lambda *args, **kwargs: {"success": True},
            "get_file_info": lambda *args, **kwargs: {
                "exists": True,
                "size": 1024000,
                "last_modified": datetime.utcnow().isoformat()
            }
        }
    
    @staticmethod
    def mock_ai_service():
        """Mock AI service responses"""
        return {
            "transcribe": lambda *args, **kwargs: {
                "text": "This is a test transcription",
                "language": "en",
                "confidence": 0.95
            },
            "detect_objects": lambda *args, **kwargs: {
                "objects": [
                    {"label": "person", "confidence": 0.92},
                    {"label": "car", "confidence": 0.87}
                ]
            },
            "generate_tags": lambda *args, **kwargs: {
                "tags": ["outdoor", "daytime", "urban"]
            }
        }


# Async test helpers
async def wait_for_condition(condition_func, timeout=5, interval=0.1):
    """Wait for a condition to be true"""
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    return False


# Performance test helpers
class PerformanceTestUtils:
    """Utilities for performance testing"""
    
    @staticmethod
    async def measure_response_time(async_func, *args, **kwargs):
        """Measure response time of an async function"""
        start_time = asyncio.get_event_loop().time()
        result = await async_func(*args, **kwargs)
        end_time = asyncio.get_event_loop().time()
        return result, end_time - start_time
    
    @staticmethod
    async def concurrent_requests(async_func, num_requests=10, *args, **kwargs):
        """Make concurrent requests and measure performance"""
        tasks = [async_func(*args, **kwargs) for _ in range(num_requests)]
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        return {
            "total_time": end_time - start_time,
            "avg_time": (end_time - start_time) / num_requests,
            "requests_per_second": num_requests / (end_time - start_time),
            "results": results
        }