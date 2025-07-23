"""
Virus Scanner Service

This module provides virus scanning capabilities for uploaded files.
Supports multiple virus scanning backends including ClamAV and cloud-based services.
"""

import os
import httpx
import tempfile
import asyncio
from typing import Optional, Dict, Any, Protocol
from pathlib import Path
from abc import ABC, abstractmethod
import structlog
import pyclamd
from datetime import datetime

from ..core.config import get_settings
from ..core.exceptions import ValidationError, ServiceUnavailableError

logger = structlog.get_logger()


class VirusScanResult:
    """Result of a virus scan"""
    
    def __init__(
        self,
        clean: bool,
        threat_name: Optional[str] = None,
        scanner_name: str = "unknown",
        scan_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.clean = clean
        self.threat_name = threat_name
        self.scanner_name = scanner_name
        self.scan_time = scan_time
        self.metadata = metadata or {}
        self.scanned_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "clean": self.clean,
            "threat_name": self.threat_name,
            "scanner_name": self.scanner_name,
            "scan_time": self.scan_time,
            "scanned_at": self.scanned_at.isoformat(),
            "metadata": self.metadata
        }


class VirusScannerBackend(ABC):
    """Abstract base class for virus scanner backends"""
    
    @abstractmethod
    async def scan_file(self, file_path: str) -> VirusScanResult:
        """Scan a file for viruses"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if scanner is available"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get scanner name"""
        pass


class ClamAVScanner(VirusScannerBackend):
    """ClamAV virus scanner implementation"""
    
    def __init__(self):
        self.clamd = None
        self._init_clamd()
    
    def _init_clamd(self):
        """Initialize ClamAV daemon connection"""
        try:
            # Try network connection first (clamd running as service)
            self.clamd = pyclamd.ClamdNetworkSocket()
            if not self.clamd.ping():
                raise ConnectionError("Network socket failed")
        except:
            try:
                # Try Unix socket
                self.clamd = pyclamd.ClamdUnixSocket()
                if not self.clamd.ping():
                    raise ConnectionError("Unix socket failed")
            except:
                logger.warning("clamav_connection_failed", 
                    message="Could not connect to ClamAV daemon")
                self.clamd = None
    
    async def scan_file(self, file_path: str) -> VirusScanResult:
        """Scan file using ClamAV"""
        if not self.clamd:
            raise ServiceUnavailableError("ClamAV is not available")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run scan in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.clamd.scan_file,
                file_path
            )
            
            scan_time = asyncio.get_event_loop().time() - start_time
            
            if result is None:
                # File is clean
                return VirusScanResult(
                    clean=True,
                    scanner_name=self.get_name(),
                    scan_time=scan_time
                )
            
            # Parse result - format: {'/path/to/file': ('FOUND', 'threat_name')}
            for path, (status, threat) in result.items():
                if status == 'FOUND':
                    logger.warning(
                        "virus_detected",
                        file_path=file_path,
                        threat_name=threat,
                        scanner="ClamAV"
                    )
                    return VirusScanResult(
                        clean=False,
                        threat_name=threat,
                        scanner_name=self.get_name(),
                        scan_time=scan_time
                    )
            
            # No threats found
            return VirusScanResult(
                clean=True,
                scanner_name=self.get_name(),
                scan_time=scan_time
            )
            
        except Exception as e:
            logger.error("clamav_scan_error", error=str(e), file_path=file_path)
            raise ValidationError(f"Virus scan failed: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if ClamAV is available"""
        if not self.clamd:
            self._init_clamd()
        
        if self.clamd:
            try:
                return self.clamd.ping()
            except:
                return False
        return False
    
    def get_name(self) -> str:
        """Get scanner name"""
        return "ClamAV"


class VirusTotalScanner(VirusScannerBackend):
    """VirusTotal API scanner implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.virustotal.com/api/v3"
        self.client = httpx.AsyncClient(
            headers={"x-apikey": api_key},
            timeout=30.0
        )
    
    async def scan_file(self, file_path: str) -> VirusScanResult:
        """Scan file using VirusTotal API"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Check file size (VirusTotal has 32MB limit for free tier)
            file_size = os.path.getsize(file_path)
            if file_size > 32 * 1024 * 1024:
                logger.warning(
                    "virustotal_file_too_large",
                    file_path=file_path,
                    size=file_size
                )
                return VirusScanResult(
                    clean=True,
                    scanner_name=self.get_name(),
                    scan_time=0,
                    metadata={"skipped": True, "reason": "file_too_large"}
                )
            
            # Upload file
            with open(file_path, 'rb') as f:
                files = {"file": (Path(file_path).name, f)}
                response = await self.client.post(
                    f"{self.base_url}/files",
                    files=files
                )
            
            if response.status_code != 200:
                raise ValidationError(f"VirusTotal upload failed: {response.status_code}")
            
            data = response.json()
            analysis_id = data["data"]["id"]
            
            # Poll for results
            max_attempts = 30
            for attempt in range(max_attempts):
                await asyncio.sleep(2)  # Wait 2 seconds between polls
                
                response = await self.client.get(
                    f"{self.base_url}/analyses/{analysis_id}"
                )
                
                if response.status_code != 200:
                    continue
                
                analysis = response.json()
                status = analysis["data"]["attributes"]["status"]
                
                if status == "completed":
                    stats = analysis["data"]["attributes"]["stats"]
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)
                    
                    scan_time = asyncio.get_event_loop().time() - start_time
                    
                    if malicious > 0 or suspicious > 0:
                        logger.warning(
                            "virus_detected",
                            file_path=file_path,
                            malicious_count=malicious,
                            suspicious_count=suspicious,
                            scanner="VirusTotal"
                        )
                        return VirusScanResult(
                            clean=False,
                            threat_name=f"{malicious} malicious, {suspicious} suspicious detections",
                            scanner_name=self.get_name(),
                            scan_time=scan_time,
                            metadata={
                                "stats": stats,
                                "analysis_id": analysis_id
                            }
                        )
                    
                    return VirusScanResult(
                        clean=True,
                        scanner_name=self.get_name(),
                        scan_time=scan_time,
                        metadata={
                            "stats": stats,
                            "analysis_id": analysis_id
                        }
                    )
            
            # Timeout waiting for results
            raise ValidationError("VirusTotal scan timeout")
            
        except Exception as e:
            logger.error("virustotal_scan_error", error=str(e), file_path=file_path)
            raise ValidationError(f"VirusTotal scan failed: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if VirusTotal is available"""
        try:
            response = await self.client.get(f"{self.base_url}/users/current")
            return response.status_code == 200
        except:
            return False
    
    def get_name(self) -> str:
        """Get scanner name"""
        return "VirusTotal"


class HybridAnalysisScanner(VirusScannerBackend):
    """Hybrid Analysis (CrowdStrike Falcon Sandbox) scanner implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.hybrid-analysis.com/api/v2"
        self.client = httpx.AsyncClient(
            headers={
                "api-key": api_key,
                "User-Agent": "MAMS Asset Management"
            },
            timeout=60.0
        )
    
    async def scan_file(self, file_path: str) -> VirusScanResult:
        """Scan file using Hybrid Analysis API"""
        # Note: This is a simplified implementation
        # Full implementation would include file submission and result polling
        logger.info("hybrid_analysis_scan_placeholder", file_path=file_path)
        
        return VirusScanResult(
            clean=True,
            scanner_name=self.get_name(),
            scan_time=0,
            metadata={"placeholder": True}
        )
    
    async def is_available(self) -> bool:
        """Check if Hybrid Analysis is available"""
        # Placeholder implementation
        return False
    
    def get_name(self) -> str:
        """Get scanner name"""
        return "Hybrid Analysis"


class VirusScannerService:
    """Main virus scanner service that orchestrates multiple backends"""
    
    def __init__(self):
        self.settings = get_settings()
        self.scanners: list[VirusScannerBackend] = []
        self._initialized = False
    
    async def initialize(self):
        """Initialize available scanners"""
        if self._initialized:
            return
        
        # Initialize ClamAV if available
        try:
            clamav = ClamAVScanner()
            if await clamav.is_available():
                self.scanners.append(clamav)
                logger.info("virus_scanner_initialized", scanner="ClamAV")
        except Exception as e:
            logger.warning("clamav_init_failed", error=str(e))
        
        # Initialize cloud scanners if API keys are configured
        if self.settings.virus_scan_api_key:
            # Assume VirusTotal by default if URL not specified
            if not self.settings.virus_scan_api_url or "virustotal" in self.settings.virus_scan_api_url:
                try:
                    vt = VirusTotalScanner(self.settings.virus_scan_api_key)
                    if await vt.is_available():
                        self.scanners.append(vt)
                        logger.info("virus_scanner_initialized", scanner="VirusTotal")
                except Exception as e:
                    logger.warning("virustotal_init_failed", error=str(e))
            
            # Add other cloud scanners based on URL
            elif "hybrid-analysis" in self.settings.virus_scan_api_url:
                try:
                    ha = HybridAnalysisScanner(self.settings.virus_scan_api_key)
                    if await ha.is_available():
                        self.scanners.append(ha)
                        logger.info("virus_scanner_initialized", scanner="Hybrid Analysis")
                except Exception as e:
                    logger.warning("hybrid_analysis_init_failed", error=str(e))
        
        self._initialized = True
        
        if not self.scanners:
            logger.warning("no_virus_scanners_available")
    
    async def scan_file(
        self,
        file_path: str,
        filename: Optional[str] = None,
        fail_on_error: bool = False
    ) -> Optional[VirusScanResult]:
        """
        Scan a file for viruses using available scanners
        
        Args:
            file_path: Path to file to scan
            filename: Original filename (for logging)
            fail_on_error: If True, raise exception on scan failure
            
        Returns:
            VirusScanResult if scan completed, None if scanning disabled/unavailable
            
        Raises:
            ValidationError: If virus found or scan fails (when fail_on_error=True)
        """
        if not self.settings.enable_virus_scan:
            logger.debug("virus_scan_disabled")
            return None
        
        await self.initialize()
        
        if not self.scanners:
            if fail_on_error:
                raise ServiceUnavailableError("No virus scanners available")
            logger.warning("virus_scan_skipped", reason="no_scanners")
            return None
        
        # Try each scanner until one succeeds
        last_error = None
        for scanner in self.scanners:
            try:
                logger.info(
                    "virus_scan_started",
                    scanner=scanner.get_name(),
                    file_path=file_path,
                    filename=filename
                )
                
                result = await scanner.scan_file(file_path)
                
                logger.info(
                    "virus_scan_completed",
                    scanner=scanner.get_name(),
                    clean=result.clean,
                    scan_time=result.scan_time,
                    threat_name=result.threat_name
                )
                
                # If virus found, always raise exception
                if not result.clean:
                    raise ValidationError(
                        f"Virus detected: {result.threat_name} (scanner: {result.scanner_name})"
                    )
                
                return result
                
            except ValidationError:
                # Re-raise validation errors (virus found)
                raise
            except Exception as e:
                last_error = e
                logger.error(
                    "virus_scan_failed",
                    scanner=scanner.get_name(),
                    error=str(e),
                    file_path=file_path
                )
                continue
        
        # All scanners failed
        if fail_on_error and last_error:
            raise ValidationError(f"All virus scanners failed: {str(last_error)}")
        
        logger.warning("virus_scan_incomplete", reason="all_scanners_failed")
        return None
    
    async def scan_data(
        self,
        data: bytes,
        filename: str = "upload.tmp",
        fail_on_error: bool = False
    ) -> Optional[VirusScanResult]:
        """
        Scan data bytes for viruses
        
        Args:
            data: File data to scan
            filename: Filename for the data
            fail_on_error: If True, raise exception on scan failure
            
        Returns:
            VirusScanResult if scan completed, None if scanning disabled/unavailable
        """
        # Write data to temporary file
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(filename).suffix
        ) as tmp_file:
            tmp_file.write(data)
            tmp_path = tmp_file.name
        
        try:
            # Scan temporary file
            return await self.scan_file(tmp_path, filename, fail_on_error)
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    async def get_scanner_status(self) -> Dict[str, Any]:
        """Get status of all configured scanners"""
        await self.initialize()
        
        status = {
            "enabled": self.settings.enable_virus_scan,
            "scanners": []
        }
        
        for scanner in self.scanners:
            scanner_status = {
                "name": scanner.get_name(),
                "available": await scanner.is_available()
            }
            status["scanners"].append(scanner_status)
        
        # Add configured but unavailable scanners
        if self.settings.virus_scan_api_key and not any(
            s.get_name() == "VirusTotal" for s in self.scanners
        ):
            status["scanners"].append({
                "name": "VirusTotal",
                "available": False,
                "reason": "initialization_failed"
            })
        
        return status


# Global scanner instance
_virus_scanner: Optional[VirusScannerService] = None


def get_virus_scanner() -> VirusScannerService:
    """Get or create virus scanner service instance"""
    global _virus_scanner
    if _virus_scanner is None:
        _virus_scanner = VirusScannerService()
    return _virus_scanner