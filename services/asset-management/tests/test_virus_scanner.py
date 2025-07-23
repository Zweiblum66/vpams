"""
Tests for virus scanner service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile

from src.services.virus_scanner import (
    VirusScanResult, ClamAVScanner, VirusTotalScanner,
    VirusScannerService, get_virus_scanner
)
from src.core.exceptions import ValidationError, ServiceUnavailableError


class TestVirusScanResult:
    """Test VirusScanResult class"""
    
    def test_clean_result(self):
        """Test creating a clean scan result"""
        result = VirusScanResult(
            clean=True,
            scanner_name="TestScanner",
            scan_time=1.5
        )
        
        assert result.clean is True
        assert result.threat_name is None
        assert result.scanner_name == "TestScanner"
        assert result.scan_time == 1.5
        
    def test_infected_result(self):
        """Test creating an infected scan result"""
        result = VirusScanResult(
            clean=False,
            threat_name="Test.Virus.A",
            scanner_name="TestScanner",
            scan_time=2.0
        )
        
        assert result.clean is False
        assert result.threat_name == "Test.Virus.A"
        assert result.scanner_name == "TestScanner"
        assert result.scan_time == 2.0
    
    def test_to_dict(self):
        """Test converting result to dictionary"""
        result = VirusScanResult(
            clean=True,
            scanner_name="TestScanner",
            scan_time=1.0,
            metadata={"test": "data"}
        )
        
        data = result.to_dict()
        assert data["clean"] is True
        assert data["scanner_name"] == "TestScanner"
        assert data["scan_time"] == 1.0
        assert data["metadata"] == {"test": "data"}
        assert "scanned_at" in data


class TestClamAVScanner:
    """Test ClamAV scanner implementation"""
    
    @pytest.mark.asyncio
    async def test_scan_clean_file(self):
        """Test scanning a clean file"""
        scanner = ClamAVScanner()
        
        # Mock ClamAV daemon
        mock_clamd = Mock()
        mock_clamd.ping.return_value = True
        mock_clamd.scan_file.return_value = None  # None means clean
        scanner.clamd = mock_clamd
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"clean content")
            tmp_path = tmp.name
        
        try:
            result = await scanner.scan_file(tmp_path)
            
            assert result.clean is True
            assert result.threat_name is None
            assert result.scanner_name == "ClamAV"
            assert result.scan_time > 0
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_scan_infected_file(self):
        """Test scanning an infected file"""
        scanner = ClamAVScanner()
        
        # Mock ClamAV daemon
        mock_clamd = Mock()
        mock_clamd.ping.return_value = True
        mock_clamd.scan_file.return_value = {
            '/tmp/test.file': ('FOUND', 'Test.Virus.A')
        }
        scanner.clamd = mock_clamd
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"infected content")
            tmp_path = tmp.name
        
        try:
            result = await scanner.scan_file(tmp_path)
            
            assert result.clean is False
            assert result.threat_name == "Test.Virus.A"
            assert result.scanner_name == "ClamAV"
            assert result.scan_time > 0
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_scanner_unavailable(self):
        """Test when ClamAV is not available"""
        scanner = ClamAVScanner()
        scanner.clamd = None
        
        with pytest.raises(ServiceUnavailableError):
            await scanner.scan_file("/tmp/test.file")
    
    @pytest.mark.asyncio
    async def test_is_available(self):
        """Test checking scanner availability"""
        scanner = ClamAVScanner()
        
        # Test when available
        mock_clamd = Mock()
        mock_clamd.ping.return_value = True
        scanner.clamd = mock_clamd
        
        assert await scanner.is_available() is True
        
        # Test when not available
        mock_clamd.ping.side_effect = Exception("Connection failed")
        assert await scanner.is_available() is False
        
        # Test when clamd is None
        scanner.clamd = None
        assert await scanner.is_available() is False


class TestVirusTotalScanner:
    """Test VirusTotal scanner implementation"""
    
    @pytest.mark.asyncio
    async def test_scan_clean_file(self):
        """Test scanning a clean file with VirusTotal"""
        scanner = VirusTotalScanner("test-api-key")
        
        # Mock HTTP client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"id": "analysis-123"}
        }
        
        mock_analysis_response = AsyncMock()
        mock_analysis_response.status_code = 200
        mock_analysis_response.json.return_value = {
            "data": {
                "attributes": {
                    "status": "completed",
                    "stats": {
                        "malicious": 0,
                        "suspicious": 0,
                        "undetected": 60,
                        "harmless": 0
                    }
                }
            }
        }
        
        scanner.client = AsyncMock()
        scanner.client.post.return_value = mock_response
        scanner.client.get.return_value = mock_analysis_response
        
        # Create small test file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"clean content")
            tmp_path = tmp.name
        
        try:
            result = await scanner.scan_file(tmp_path)
            
            assert result.clean is True
            assert result.scanner_name == "VirusTotal"
            assert result.metadata["analysis_id"] == "analysis-123"
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_scan_infected_file(self):
        """Test scanning an infected file with VirusTotal"""
        scanner = VirusTotalScanner("test-api-key")
        
        # Mock HTTP client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"id": "analysis-123"}
        }
        
        mock_analysis_response = AsyncMock()
        mock_analysis_response.status_code = 200
        mock_analysis_response.json.return_value = {
            "data": {
                "attributes": {
                    "status": "completed",
                    "stats": {
                        "malicious": 5,
                        "suspicious": 2,
                        "undetected": 53,
                        "harmless": 0
                    }
                }
            }
        }
        
        scanner.client = AsyncMock()
        scanner.client.post.return_value = mock_response
        scanner.client.get.return_value = mock_analysis_response
        
        # Create small test file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"infected content")
            tmp_path = tmp.name
        
        try:
            result = await scanner.scan_file(tmp_path)
            
            assert result.clean is False
            assert "5 malicious, 2 suspicious" in result.threat_name
            assert result.scanner_name == "VirusTotal"
        finally:
            Path(tmp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_file_too_large(self):
        """Test handling of files too large for VirusTotal"""
        scanner = VirusTotalScanner("test-api-key")
        
        # Create test file path (doesn't need to exist for size check)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * 100)  # Small file
            tmp_path = tmp.name
        
        # Mock file size check
        with patch("os.path.getsize", return_value=33 * 1024 * 1024):  # 33MB
            result = await scanner.scan_file(tmp_path)
        
        assert result.clean is True
        assert result.metadata["skipped"] is True
        assert result.metadata["reason"] == "file_too_large"
        
        Path(tmp_path).unlink()


class TestVirusScannerService:
    """Test main virus scanner service"""
    
    @pytest.mark.asyncio
    async def test_scan_with_no_scanners(self):
        """Test scanning when no scanners are available"""
        service = VirusScannerService()
        service._initialized = True
        service.scanners = []
        
        # Should return None when no scanners
        result = await service.scan_file("/tmp/test.file")
        assert result is None
        
        # Should raise when fail_on_error=True
        with pytest.raises(ServiceUnavailableError):
            await service.scan_file("/tmp/test.file", fail_on_error=True)
    
    @pytest.mark.asyncio
    async def test_scan_with_virus_found(self):
        """Test when virus is found"""
        service = VirusScannerService()
        
        # Create mock scanner that finds virus
        mock_scanner = AsyncMock()
        mock_scanner.get_name.return_value = "TestScanner"
        mock_scanner.scan_file.return_value = VirusScanResult(
            clean=False,
            threat_name="Test.Virus",
            scanner_name="TestScanner"
        )
        
        service._initialized = True
        service.scanners = [mock_scanner]
        
        with pytest.raises(ValidationError) as exc_info:
            await service.scan_file("/tmp/test.file")
        
        assert "Virus detected: Test.Virus" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_scan_data(self):
        """Test scanning data bytes"""
        service = VirusScannerService()
        
        # Create mock scanner
        mock_scanner = AsyncMock()
        mock_scanner.get_name.return_value = "TestScanner"
        mock_scanner.scan_file.return_value = VirusScanResult(
            clean=True,
            scanner_name="TestScanner"
        )
        
        service._initialized = True
        service.scanners = [mock_scanner]
        
        result = await service.scan_data(b"test content", "test.txt")
        
        assert result.clean is True
        assert result.scanner_name == "TestScanner"
    
    @pytest.mark.asyncio
    async def test_get_scanner_status(self):
        """Test getting scanner status"""
        service = VirusScannerService()
        
        # Create mock scanner
        mock_scanner = AsyncMock()
        mock_scanner.get_name.return_value = "TestScanner"
        mock_scanner.is_available.return_value = True
        
        service._initialized = True
        service.scanners = [mock_scanner]
        service.settings.enable_virus_scan = True
        
        status = await service.get_scanner_status()
        
        assert status["enabled"] is True
        assert len(status["scanners"]) == 1
        assert status["scanners"][0]["name"] == "TestScanner"
        assert status["scanners"][0]["available"] is True
    
    @pytest.mark.asyncio
    async def test_scan_disabled(self):
        """Test when virus scanning is disabled"""
        service = VirusScannerService()
        service.settings.enable_virus_scan = False
        
        result = await service.scan_file("/tmp/test.file")
        assert result is None


def test_get_virus_scanner():
    """Test getting virus scanner singleton"""
    scanner1 = get_virus_scanner()
    scanner2 = get_virus_scanner()
    
    assert scanner1 is scanner2  # Should be same instance