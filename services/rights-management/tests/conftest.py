"""Pytest configuration and fixtures for Rights Management service tests."""
import pytest
import asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from datetime import datetime, date, timedelta
import uuid

from src.main import app
from src.db.models import Base, RightsParty, License, UsageRecord, ComplianceAlert, UsageType
from src.core.config import settings
from src.core.database import get_db


# Override database URL for testing
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.split("/")[-1], "test_rights_management"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database and provide session."""
    # Create test engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        # Initialize usage types
        await _init_usage_types(session)
        yield session
    
    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


async def _init_usage_types(session: AsyncSession):
    """Initialize standard usage types"""
    usage_types = [
        {"id": "broadcast", "name": "Broadcast", "description": "Television and radio broadcast"},
        {"id": "streaming", "name": "Streaming", "description": "Online streaming platforms"},
        {"id": "sync", "name": "Synchronization", "description": "Music synchronization with visual media"},
        {"id": "master", "name": "Master Recording", "description": "Master recording rights"},
        {"id": "mechanical", "name": "Mechanical", "description": "Mechanical reproduction rights"},
        {"id": "theatrical", "name": "Theatrical", "description": "Cinema and theatrical exhibition"},
        {"id": "home_video", "name": "Home Video", "description": "DVD, Blu-ray, and digital download"}
    ]
    
    for usage_type_data in usage_types:
        usage_type = UsageType(**usage_type_data)
        session.add(usage_type)
    
    await session.commit()


@pytest.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with test database."""
    # Override dependency
    app.dependency_overrides[get_db] = lambda: test_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    """Provide authentication headers for testing."""
    # In a real scenario, this would generate a valid JWT token
    return {
        "Authorization": "Bearer test-token",
        "X-User-ID": "test-user-123",
        "X-User-Email": "test@example.com",
        "X-User-Permissions": "rights:read,rights:write,rights:admin"
    }


@pytest.fixture
def test_user() -> Dict[str, Any]:
    """Provide test user data."""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "permissions": ["rights:read", "rights:write", "rights:admin"]
    }


@pytest.fixture
async def sample_parties(test_db: AsyncSession) -> Dict[str, str]:
    """Create sample rights parties."""
    licensor = RightsParty(
        party_type="licensor",
        name="Sample Studios",
        legal_name="Sample Studios LLC",
        contact_email="legal@samplestudios.com",
        contact_phone="+1-555-0100",
        address="123 Studio Way, Hollywood, CA 90028",
        country="USA",
        tax_id="12-3456789",
        is_active=True,
        metadata={
            "founded": "2010",
            "employees": 500,
            "specialties": ["film", "television", "streaming"]
        }
    )
    
    licensee = RightsParty(
        party_type="licensee",
        name="Global Broadcasting Network",
        legal_name="GBN Corporation",
        contact_email="licensing@gbn.com",
        contact_phone="+1-555-0200",
        address="456 Broadcast Plaza, New York, NY 10001",
        country="USA",
        tax_id="98-7654321",
        is_active=True,
        metadata={
            "network_reach": "150 countries",
            "platforms": ["television", "streaming", "mobile"]
        }
    )
    
    agent = RightsParty(
        party_type="agent",
        name="Media Rights Agency",
        contact_email="deals@mediarightsagency.com",
        contact_phone="+1-555-0300",
        country="USA",
        percentage_share=10.0,
        is_active=True
    )
    
    test_db.add_all([licensor, licensee, agent])
    await test_db.commit()
    
    return {
        "licensor_id": str(licensor.id),
        "licensee_id": str(licensee.id),
        "agent_id": str(agent.id)
    }


@pytest.fixture
async def sample_license(test_db: AsyncSession, sample_parties: Dict[str, str]) -> Dict[str, Any]:
    """Create a sample license."""
    asset_id = str(uuid.uuid4())
    
    license = License(
        license_number="LIC-SAMPLE-001",
        license_type="broadcast",
        status="active",
        title="Sample Broadcast License",
        description="Sample license for testing purposes",
        asset_id=asset_id,
        licensor_id=sample_parties["licensor_id"],
        licensee_id=sample_parties["licensee_id"],
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        signed_date=date.today() - timedelta(days=30),
        geographic_scope="territory",
        countries=["US", "CA", "MX"],
        license_fee=100000.0,
        currency="USD",
        royalty_rate=15.0,
        minimum_guarantee=20000.0,
        max_usage_count=100,
        max_duration_seconds=7200,
        exclusivity=False,
        sublicensing_allowed=True,
        metadata={
            "contract_reference": "CONT-2025-001",
            "payment_terms": "net_30",
            "renewal_option": True
        },
        notes="Standard broadcast license with North American rights"
    )
    
    test_db.add(license)
    await test_db.commit()
    await test_db.refresh(license)
    
    return {
        "license_id": str(license.id),
        "asset_id": asset_id,
        "license_number": license.license_number
    }


@pytest.fixture
async def sample_usage_records(
    test_db: AsyncSession, 
    sample_license: Dict[str, Any]
) -> list:
    """Create sample usage records."""
    usage_records = []
    
    for i in range(5):
        usage = UsageRecord(
            license_id=sample_license["license_id"],
            asset_id=sample_license["asset_id"],
            user_id=str(uuid.uuid4()),
            usage_type="broadcast",
            usage_date=datetime.utcnow() - timedelta(days=i),
            duration_seconds=1800 + (i * 300),
            usage_count=1,
            platform="Television",
            channel=f"Channel {i+1}",
            program_title="Evening News",
            country="USA" if i % 2 == 0 else "CA",
            revenue_generated=1000.0 * (i + 1),
            royalty_due=150.0 * (i + 1),
            metadata={
                "time_slot": "prime_time" if i < 2 else "regular",
                "audience_size": 100000 * (i + 1)
            }
        )
        test_db.add(usage)
        usage_records.append(usage)
    
    await test_db.commit()
    
    return [{"id": str(record.id), "revenue": record.revenue_generated} for record in usage_records]


@pytest.fixture
async def sample_compliance_alerts(
    test_db: AsyncSession,
    sample_license: Dict[str, Any]
) -> list:
    """Create sample compliance alerts."""
    alerts = []
    
    alert_configs = [
        {
            "alert_type": "expiration_warning",
            "severity": "medium",
            "title": "License Expiring Soon",
            "description": "License will expire in 30 days"
        },
        {
            "alert_type": "usage_limit_warning",
            "severity": "high",
            "title": "Usage Limit Approaching",
            "description": "80% of usage limit has been reached"
        },
        {
            "alert_type": "geographic_violation",
            "severity": "critical",
            "title": "Geographic Restriction Violated",
            "description": "Usage detected in restricted territory"
        }
    ]
    
    for config in alert_configs:
        alert = ComplianceAlert(
            license_id=sample_license["license_id"],
            asset_id=sample_license["asset_id"],
            **config,
            is_resolved=False,
            metadata={
                "detected_at": datetime.utcnow().isoformat(),
                "detection_method": "automated"
            }
        )
        test_db.add(alert)
        alerts.append(alert)
    
    await test_db.commit()
    
    return [{"id": str(alert.id), "type": alert.alert_type} for alert in alerts]


@pytest.fixture
def mock_external_services(monkeypatch):
    """Mock external service calls."""
    # Mock geolocation service
    async def mock_get_ip_geolocation(ip_address: str):
        return {
            "ip_address": ip_address,
            "country_code": "US",
            "country_name": "United States",
            "region": "CA",
            "city": "Los Angeles",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "timezone": "America/Los_Angeles",
            "is_vpn": False
        }
    
    # Mock file storage service
    async def mock_upload_report(file_path: str, content: bytes):
        return f"/reports/{uuid.uuid4()}.pdf"
    
    # Apply mocks
    monkeypatch.setattr(
        "src.services.geo_blocking_service.GeoBlockingService.get_ip_geolocation",
        mock_get_ip_geolocation
    )
    
    return {
        "get_ip_geolocation": mock_get_ip_geolocation,
        "upload_report": mock_upload_report
    }