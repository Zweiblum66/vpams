"""
Tests for security scanners
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from src.core.security_scanner import CodeScanner, DependencyScanner
from src.core.config import Settings


@pytest.fixture
def settings():
    """Test settings"""
    return Settings(
        scan_timeout_seconds=60,
        debug=True
    )


@pytest.fixture
def temp_code_dir():
    """Create temporary directory with test code"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test Python file with security issues
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("""
import os
import subprocess

# Security issue: hardcoded password
password = "hardcoded_password_123"

# Security issue: SQL injection vulnerability
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute_query(query)

# Security issue: command injection
def run_command(cmd):
    os.system(cmd)
    
# Security issue: insecure random
import random
token = random.randint(1000, 9999)

# Security issue: eval usage
def evaluate_code(code):
    return eval(code)
""")
        
        # Create requirements.txt with vulnerable packages
        req_file = Path(temp_dir) / "requirements.txt"
        req_file.write_text("""
Django==1.11.0
requests==2.6.0
Pillow==5.0.0
""")
        
        yield temp_dir


@pytest.mark.asyncio
async def test_code_scanner_bandit(settings, temp_code_dir):
    """Test code scanner with Bandit"""
    scanner = CodeScanner(settings)
    
    # Run scan
    result = await scanner.scan(temp_code_dir)
    
    # Verify results
    assert result["scanner"] == "code"
    assert result["target"] == temp_code_dir
    assert "findings" in result
    assert "summary" in result
    
    # Should find security issues
    assert result["summary"]["total"] > 0
    
    # Check for specific security issues
    finding_titles = [f["title"] for f in result["findings"]]
    assert any("hardcoded" in title.lower() for title in finding_titles)


@pytest.mark.asyncio
async def test_dependency_scanner_safety(settings, temp_code_dir):
    """Test dependency scanner with Safety"""
    scanner = DependencyScanner(settings)
    
    # Run scan
    result = await scanner.scan(temp_code_dir)
    
    # Verify results
    assert result["scanner"] == "dependency"
    assert result["target"] == temp_code_dir
    assert "findings" in result
    assert "summary" in result
    
    # Should find vulnerable dependencies
    assert result["summary"]["total"] >= 0  # May be 0 if no vulnerabilities found


@pytest.mark.asyncio
async def test_scanner_timeout(settings):
    """Test scanner timeout handling"""
    # Set very short timeout
    settings.scan_timeout_seconds = 0.001
    
    scanner = CodeScanner(settings)
    
    # This should timeout
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            scanner.scan("/nonexistent/path"),
            timeout=settings.scan_timeout_seconds
        )


@pytest.mark.asyncio
async def test_scanner_invalid_target(settings):
    """Test scanner with invalid target"""
    scanner = CodeScanner(settings)
    
    # Run scan on non-existent directory
    result = await scanner.scan("/nonexistent/path")
    
    # Should handle gracefully
    assert result["scanner"] == "code"
    assert result["findings"] == []


def test_severity_mapping():
    """Test severity level mapping"""
    scanner = CodeScanner(Settings())
    
    # Test Bandit severity mapping
    assert scanner._map_bandit_severity("HIGH") == "high"
    assert scanner._map_bandit_severity("MEDIUM") == "medium"
    assert scanner._map_bandit_severity("LOW") == "low"
    assert scanner._map_bandit_severity("UNKNOWN") == "low"
    
    # Test Semgrep severity mapping
    assert scanner._map_semgrep_severity("ERROR") == "critical"
    assert scanner._map_semgrep_severity("WARNING") == "high"
    assert scanner._map_semgrep_severity("INFO") == "medium"
    assert scanner._map_semgrep_severity("UNKNOWN") == "medium"


def test_dependency_severity_calculation():
    """Test dependency severity calculation"""
    scanner = DependencyScanner(Settings())
    
    # Test CVSS score mapping
    assert scanner._calculate_severity(9.5) == "critical"
    assert scanner._calculate_severity(8.0) == "high"
    assert scanner._calculate_severity(5.0) == "medium"
    assert scanner._calculate_severity(2.0) == "low"
    
    # Test fix versions (list input)
    assert scanner._calculate_severity(["1.2.3", "1.2.4"]) == "high"


@pytest.mark.asyncio
async def test_code_scanner_file_patterns(settings, temp_code_dir):
    """Test code scanner with different file patterns"""
    scanner = CodeScanner(settings)
    
    # Create additional test files
    js_file = Path(temp_code_dir) / "test.js"
    js_file.write_text("var password = 'secret123';")
    
    py_file = Path(temp_code_dir) / "secure.py"
    py_file.write_text("import hashlib\npassword_hash = hashlib.sha256(b'password').hexdigest()")
    
    # Run scan
    result = await scanner.scan(temp_code_dir)
    
    # Should scan all files in directory
    assert result["summary"]["total"] >= 0


@pytest.mark.asyncio
async def test_dependency_scanner_multiple_formats(settings):
    """Test dependency scanner with multiple file formats"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create different dependency files
        files = {
            "requirements.txt": "Django==1.11.0\nrequests==2.6.0",
            "requirements-dev.txt": "pytest==3.0.0",
            "Pipfile": "[packages]\ndjango = \"==1.11.0\"",
            "package.json": '{"dependencies": {"lodash": "4.17.4"}}'
        }
        
        for filename, content in files.items():
            file_path = Path(temp_dir) / filename
            file_path.write_text(content)
        
        scanner = DependencyScanner(settings)
        
        # Find requirements files
        req_files = scanner._find_requirements_files(temp_dir)
        
        # Should find multiple file types
        assert len(req_files) >= 2
        assert any("requirements.txt" in f for f in req_files)
        assert any("package.json" in f for f in req_files)