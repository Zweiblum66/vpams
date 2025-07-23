"""
Tests for compliance checkers
"""

import pytest
import tempfile
from pathlib import Path

from src.core.compliance_checker import ISO27001Checker, GDPRChecker, SOC2Checker
from src.core.config import Settings


@pytest.fixture
def settings():
    """Test settings"""
    return Settings()


@pytest.fixture
def test_codebase():
    """Create test codebase with security patterns"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files with compliance-relevant patterns
        
        # Authentication and access control patterns
        auth_file = Path(temp_dir) / "auth.py"
        auth_file.write_text("""
from functools import wraps
import jwt
from passlib.hash import bcrypt

@login_required
def protected_view(request):
    pass

def authenticate_user(username, password):
    user = get_user(username)
    if user and bcrypt.verify(password, user.password_hash):
        return user
    return None

@require_role('admin')
def admin_only_view(request):
    pass

def check_permissions(user, resource):
    return user.has_permission(resource)
""")
        
        # Cryptography patterns
        crypto_file = Path(temp_dir) / "crypto.py"
        crypto_file.write_text("""
from cryptography.fernet import Fernet
import hashlib
import bcrypt

def encrypt_data(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode())

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def generate_key():
    return Fernet.generate_key()
""")
        
        # Logging and monitoring patterns
        logging_file = Path(temp_dir) / "logging.py"
        logging_file.write_text("""
import structlog
import logging

logger = structlog.get_logger()

def log_security_event(event_type, user_id, details):
    logger.info("security_event", 
                event_type=event_type,
                user_id=user_id,
                details=details)

def audit_log(action, user, resource):
    logging.info(f"AUDIT: {user} performed {action} on {resource}")

def monitor_failed_logins(username):
    logger.warning("failed_login", username=username)
""")
        
        # GDPR compliance patterns
        gdpr_file = Path(temp_dir) / "privacy.py"
        gdpr_file.write_text("""
def get_user_consent(user_id, purpose):
    consent = UserConsent.objects.filter(
        user_id=user_id,
        purpose=purpose,
        is_active=True
    ).first()
    return consent is not None

def process_data_deletion_request(user_id):
    # Right to be forgotten implementation
    user_data = UserData.objects.filter(user_id=user_id)
    for data in user_data:
        data.anonymize()
        data.save()

def validate_data_accuracy(user_data):
    # Data accuracy validation
    errors = []
    if not user_data.email_verified:
        errors.append("Email not verified")
    return errors
""")
        
        # Business continuity patterns
        backup_file = Path(temp_dir) / "backup.py"
        backup_file.write_text("""
def create_backup(data_type):
    backup_service = BackupService()
    return backup_service.create_backup(data_type)

def disaster_recovery_plan():
    # Disaster recovery implementation
    restore_from_backup()
    failover_to_secondary_site()

def test_business_continuity():
    # Test business continuity procedures
    pass
""")
        
        yield temp_dir


@pytest.mark.asyncio
async def test_iso27001_checker(settings, test_codebase):
    """Test ISO 27001 compliance checker"""
    checker = ISO27001Checker(settings)
    
    result = await checker.check(test_codebase)
    
    # Verify basic structure
    assert result["standard"] == "ISO 27001"
    assert result["target"] == test_codebase
    assert "controls" in result
    assert "score" in result
    assert "status" in result
    
    # Should find at least some controls
    assert len(result["controls"]) > 0
    
    # Check specific controls
    control_ids = [control["id"] for control in result["controls"]]
    assert "A.9" in control_ids  # Access Control
    assert "A.10" in control_ids  # Cryptography
    assert "A.12" in control_ids  # Operations Security
    
    # Check access control findings
    access_control = next(c for c in result["controls"] if c["id"] == "A.9")
    assert access_control["score"] > 0  # Should find authentication patterns
    
    # Check cryptography findings
    crypto_control = next(c for c in result["controls"] if c["id"] == "A.10")
    assert crypto_control["score"] > 0  # Should find encryption patterns


@pytest.mark.asyncio
async def test_gdpr_checker(settings, test_codebase):
    """Test GDPR compliance checker"""
    checker = GDPRChecker(settings)
    
    result = await checker.check(test_codebase)
    
    # Verify basic structure
    assert result["standard"] == "GDPR"
    assert result["target"] == test_codebase
    assert "principles" in result
    assert "score" in result
    assert "status" in result
    
    # Should find GDPR principles
    assert len(result["principles"]) > 0
    
    # Check specific principles
    principle_names = [p["name"] for p in result["principles"]]
    assert "Lawfulness, fairness and transparency" in principle_names
    assert "Accountability" in principle_names
    
    # Check consent management
    lawfulness = next(p for p in result["principles"] 
                     if p["name"] == "Lawfulness, fairness and transparency")
    assert lawfulness["score"] > 0  # Should find consent patterns


@pytest.mark.asyncio
async def test_soc2_checker(settings, test_codebase):
    """Test SOC 2 compliance checker"""
    checker = SOC2Checker(settings)
    
    result = await checker.check(test_codebase)
    
    # Verify basic structure
    assert result["standard"] == "SOC 2 Type II"
    assert result["target"] == test_codebase
    assert "criteria" in result
    assert "score" in result
    assert "status" in result
    
    # Should find SOC 2 criteria
    assert len(result["criteria"]) > 0
    
    # Check specific criteria
    criteria_names = [c["name"] for c in result["criteria"]]
    assert "Security" in criteria_names
    assert "Availability" in criteria_names
    
    # Check security criterion
    security = next(c for c in result["criteria"] if c["name"] == "Security")
    assert security["score"] > 0  # Should find security patterns


@pytest.mark.asyncio
async def test_pattern_scanning(settings):
    """Test pattern scanning functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create file with specific patterns
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("""
import jwt
from passlib import hash
import logging

def authenticate_user():
    pass

logger = logging.getLogger(__name__)
""")
        
        checker = ISO27001Checker(settings)
        
        # Test pattern scanning
        patterns = ["jwt", "authenticate", "logging"]
        found = await checker._scan_for_patterns(temp_dir, patterns)
        
        # Should find all patterns
        assert len(found) >= 3
        assert any("jwt" in f for f in found)
        assert any("authenticate" in f for f in found)
        assert any("logging" in f for f in found)


@pytest.mark.asyncio
async def test_empty_codebase(settings):
    """Test compliance checkers with empty codebase"""
    with tempfile.TemporaryDirectory() as temp_dir:
        checker = ISO27001Checker(settings)
        
        result = await checker.check(temp_dir)
        
        # Should handle empty codebase gracefully
        assert result["score"] == 0.0
        assert result["status"] == "non_compliant"
        assert len(result["controls"]) > 0
        
        # All controls should have zero score
        for control in result["controls"]:
            assert control["score"] == 0.0


@pytest.mark.asyncio
async def test_compliance_scoring(settings, test_codebase):
    """Test compliance scoring logic"""
    checker = ISO27001Checker(settings)
    
    result = await checker.check(test_codebase)
    
    # Score should be between 0 and 1
    assert 0.0 <= result["score"] <= 1.0
    
    # Status should be based on score
    if result["score"] >= 0.8:
        assert result["status"] == "compliant"
    else:
        assert result["status"] == "non_compliant"
    
    # Control scores should be consistent
    for control in result["controls"]:
        assert 0.0 <= control["score"] <= 1.0
        
        # Control score should match requirement pass rate
        total_reqs = len(control["requirements"])
        passed_reqs = sum(1 for req in control["requirements"] if req["status"] == "pass")
        expected_score = passed_reqs / total_reqs if total_reqs > 0 else 0.0
        assert abs(control["score"] - expected_score) < 0.001


@pytest.mark.asyncio
async def test_gdpr_data_patterns(settings):
    """Test GDPR-specific data handling patterns"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create file with GDPR-relevant patterns
        gdpr_file = Path(temp_dir) / "gdpr.py"
        gdpr_file.write_text("""
def collect_user_data(user_id, purpose):
    # Only collect necessary data
    required_fields = get_required_fields(purpose)
    return collect_only_required(user_id, required_fields)

def retention_policy(data_type):
    # Data retention based on type
    if data_type == "user_activity":
        return timedelta(days=365)
    elif data_type == "financial":
        return timedelta(days=2555)  # 7 years
    
def anonymize_user_data(user_id):
    # Data anonymization for privacy
    user_data = get_user_data(user_id)
    return anonymize(user_data)
""")
        
        checker = GDPRChecker(settings)
        result = await checker.check(temp_dir)
        
        # Should find data minimization patterns
        minimization = next(p for p in result["principles"] 
                          if p["name"] == "Data minimisation")
        assert minimization["score"] > 0
        
        # Should find retention patterns
        storage = next(p for p in result["principles"] 
                      if p["name"] == "Storage limitation")
        assert storage["score"] > 0


@pytest.mark.asyncio
async def test_soc2_availability_patterns(settings):
    """Test SOC 2 availability patterns"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create file with availability patterns
        availability_file = Path(temp_dir) / "availability.py"
        availability_file.write_text("""
def setup_failover():
    # Failover configuration
    primary_db = connect_to_primary()
    secondary_db = connect_to_secondary()
    setup_replication(primary_db, secondary_db)

def monitor_uptime():
    # Uptime monitoring
    health_check = perform_health_check()
    if not health_check.is_healthy():
        trigger_alert()

def backup_system():
    # Regular backup procedures
    create_database_backup()
    verify_backup_integrity()
""")
        
        checker = SOC2Checker(settings)
        result = await checker.check(temp_dir)
        
        # Should find availability patterns
        availability = next(c for c in result["criteria"] 
                          if c["name"] == "Availability")
        assert availability["score"] > 0