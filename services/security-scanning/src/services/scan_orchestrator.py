"""
Scan orchestrator for coordinating and managing security scans.

Manages different types of security scans including network, web application,
infrastructure, and vulnerability scanning.
"""

import asyncio
import uuid
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import structlog

from ..core.config import get_settings
from ..core.exceptions import (
    ScanExecutionError, InvalidTargetError, ScanLimitExceededError,
    ScanTimeoutError
)
from ..models.schemas import (
    ScanRequest, ScanResult, ScanStatus, ScanType, VulnerabilityLevel
)
from .network_scanner import NetworkScanner
from .web_scanner import WebScanner
from .vulnerability_scanner import VulnerabilityScanner
from .ssl_scanner import SSLScanner
from .infrastructure_scanner import InfrastructureScanner
from .report_generator import ReportGenerator


logger = structlog.get_logger()


class ScanState(Enum):
    """Scan execution states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ScanOrchestrator:
    """Main orchestrator for all security scanning operations."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Scan engines
        self.network_scanner: Optional[NetworkScanner] = None
        self.web_scanner: Optional[WebScanner] = None
        self.vulnerability_scanner: Optional[VulnerabilityScanner] = None
        self.ssl_scanner: Optional[SSLScanner] = None
        self.infrastructure_scanner: Optional[InfrastructureScanner] = None
        self.report_generator: Optional[ReportGenerator] = None
        
        # Scan management
        self.active_scans: Dict[str, Dict[str, Any]] = {}
        self.scan_queue: asyncio.Queue = asyncio.Queue(maxsize=self.settings.scan_queue_size)
        self.scan_history: List[Dict[str, Any]] = []
        
        # Rate limiting
        self.scan_count_per_hour: Dict[str, List[datetime]] = {}
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False
        
        # Statistics
        self.stats = {
            "scans_completed": 0,
            "scans_failed": 0,
            "vulnerabilities_found": 0,
            "high_severity_findings": 0,
            "average_scan_time": 0.0,
            "last_scan": None
        }
    
    async def initialize(self) -> None:
        """Initialize scan orchestrator and all scanning engines."""
        try:
            logger.info("Initializing scan orchestrator")
            
            # Initialize scanning engines
            if self.settings.network_scan_enabled:
                self.network_scanner = NetworkScanner()
                await self.network_scanner.initialize()
                logger.info("Network scanner initialized")
            
            if self.settings.web_scan_enabled:
                self.web_scanner = WebScanner()
                await self.web_scanner.initialize()
                logger.info("Web scanner initialized")
            
            if self.settings.vuln_scan_enabled:
                self.vulnerability_scanner = VulnerabilityScanner()
                await self.vulnerability_scanner.initialize()
                logger.info("Vulnerability scanner initialized")
            
            if self.settings.ssl_scan_enabled:
                self.ssl_scanner = SSLScanner()
                await self.ssl_scanner.initialize()
                logger.info("SSL scanner initialized")
            
            if self.settings.infra_scan_enabled:
                self.infrastructure_scanner = InfrastructureScanner()
                await self.infrastructure_scanner.initialize()
                logger.info("Infrastructure scanner initialized")
            
            # Initialize report generator
            self.report_generator = ReportGenerator()
            await self.report_generator.initialize()
            logger.info("Report generator initialized")
            
            # Start background tasks
            await self._start_background_tasks()
            self._running = True
            
            logger.info(
                "Scan orchestrator initialized",
                engines_active={
                    "network": self.network_scanner is not None,
                    "web": self.web_scanner is not None,
                    "vulnerability": self.vulnerability_scanner is not None,
                    "ssl": self.ssl_scanner is not None,
                    "infrastructure": self.infrastructure_scanner is not None
                }
            )
            
        except Exception as e:
            logger.error("Failed to initialize scan orchestrator", error=str(e))
            raise ScanExecutionError(f"Initialization failed: {str(e)}")
    
    async def _start_background_tasks(self) -> None:
        """Start background processing tasks."""
        # Scan queue processor
        for _ in range(self.settings.worker_threads):
            task = asyncio.create_task(self._scan_worker())
            self._tasks.append(task)
        
        # Cleanup task
        task = asyncio.create_task(self._cleanup_task())
        self._tasks.append(task)
        
        # Statistics update task
        task = asyncio.create_task(self._stats_update_task())
        self._tasks.append(task)
        
        logger.info(f"Started {len(self._tasks)} background tasks")
    
    async def _scan_worker(self) -> None:
        """Background worker for processing scan queue."""
        while self._running:
            try:
                # Get scan request from queue
                scan_data = await self.scan_queue.get()
                
                scan_id = scan_data["scan_id"]
                scan_request = scan_data["request"]
                
                # Update scan state
                if scan_id in self.active_scans:
                    self.active_scans[scan_id]["state"] = ScanState.RUNNING
                    self.active_scans[scan_id]["started_at"] = datetime.utcnow()
                
                # Execute scan
                try:
                    result = await self._execute_scan(scan_id, scan_request)
                    
                    # Update scan with results
                    if scan_id in self.active_scans:
                        self.active_scans[scan_id]["state"] = ScanState.COMPLETED
                        self.active_scans[scan_id]["result"] = result
                        self.active_scans[scan_id]["completed_at"] = datetime.utcnow()
                    
                    self.stats["scans_completed"] += 1
                    
                except asyncio.TimeoutError:
                    if scan_id in self.active_scans:
                        self.active_scans[scan_id]["state"] = ScanState.TIMEOUT
                        self.active_scans[scan_id]["error"] = "Scan timed out"
                    
                    logger.warning("Scan timed out", scan_id=scan_id)
                    
                except Exception as e:
                    if scan_id in self.active_scans:
                        self.active_scans[scan_id]["state"] = ScanState.FAILED
                        self.active_scans[scan_id]["error"] = str(e)
                    
                    self.stats["scans_failed"] += 1
                    logger.error("Scan failed", scan_id=scan_id, error=str(e))
                
                finally:
                    self.scan_queue.task_done()
                
            except Exception as e:
                logger.error("Error in scan worker", error=str(e))
                await asyncio.sleep(1)
    
    async def _execute_scan(self, scan_id: str, request: ScanRequest) -> ScanResult:
        """Execute a security scan based on the request type."""
        start_time = time.time()
        
        try:
            logger.info(
                "Executing scan",
                scan_id=scan_id,
                scan_type=request.scan_type.value,
                target=request.target
            )
            
            # Set timeout
            timeout = self.settings.scan_timeout_minutes * 60
            if request.profile in self.settings.scan_profiles:
                profile_timeout = self.settings.scan_profiles[request.profile].get("timeout", timeout)
                timeout = min(timeout, profile_timeout)
            
            # Execute appropriate scanner
            if request.scan_type == ScanType.NETWORK:
                if not self.network_scanner:
                    raise ScanExecutionError("Network scanner not available")
                result = await asyncio.wait_for(
                    self.network_scanner.scan(request),
                    timeout=timeout
                )
                
            elif request.scan_type == ScanType.WEB_APPLICATION:
                if not self.web_scanner:
                    raise ScanExecutionError("Web scanner not available")
                result = await asyncio.wait_for(
                    self.web_scanner.scan(request),
                    timeout=timeout
                )
                
            elif request.scan_type == ScanType.VULNERABILITY:
                if not self.vulnerability_scanner:
                    raise ScanExecutionError("Vulnerability scanner not available")
                result = await asyncio.wait_for(
                    self.vulnerability_scanner.scan(request),
                    timeout=timeout
                )
                
            elif request.scan_type == ScanType.SSL_TLS:
                if not self.ssl_scanner:
                    raise ScanExecutionError("SSL scanner not available")
                result = await asyncio.wait_for(
                    self.ssl_scanner.scan(request),
                    timeout=timeout
                )
                
            elif request.scan_type == ScanType.INFRASTRUCTURE:
                if not self.infrastructure_scanner:
                    raise ScanExecutionError("Infrastructure scanner not available")
                result = await asyncio.wait_for(
                    self.infrastructure_scanner.scan(request),
                    timeout=timeout
                )
                
            elif request.scan_type == ScanType.COMPREHENSIVE:
                # Run multiple scan types
                result = await self._comprehensive_scan(request, timeout)
                
            else:
                raise ScanExecutionError(f"Unsupported scan type: {request.scan_type}")
            
            # Update statistics
            execution_time = time.time() - start_time
            self._update_scan_statistics(result, execution_time)
            
            logger.info(
                "Scan completed",
                scan_id=scan_id,
                execution_time=execution_time,
                findings_count=len(result.findings)
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Scan timed out", scan_id=scan_id, timeout=timeout)
            raise ScanTimeoutError(request.scan_type.value, timeout)
            
        except Exception as e:
            logger.error("Scan execution failed", scan_id=scan_id, error=str(e))
            raise ScanExecutionError(f"Scan execution failed: {str(e)}")
    
    async def _comprehensive_scan(self, request: ScanRequest, timeout: int) -> ScanResult:
        """Execute a comprehensive scan combining multiple scan types."""
        logger.info("Starting comprehensive scan", target=request.target)
        
        all_findings = []
        scan_details = {}
        
        # Network scan
        if self.network_scanner:
            try:
                network_request = ScanRequest(
                    target=request.target,
                    scan_type=ScanType.NETWORK,
                    profile=request.profile,
                    options=request.options
                )
                network_result = await asyncio.wait_for(
                    self.network_scanner.scan(network_request),
                    timeout=timeout // 4
                )
                all_findings.extend(network_result.findings)
                scan_details["network"] = network_result.scan_metadata
            except Exception as e:
                logger.warning("Network scan failed in comprehensive scan", error=str(e))
        
        # Web application scan
        if self.web_scanner and request.target.startswith(("http://", "https://")):
            try:
                web_request = ScanRequest(
                    target=request.target,
                    scan_type=ScanType.WEB_APPLICATION,
                    profile=request.profile,
                    options=request.options
                )
                web_result = await asyncio.wait_for(
                    self.web_scanner.scan(web_request),
                    timeout=timeout // 4
                )
                all_findings.extend(web_result.findings)
                scan_details["web"] = web_result.scan_metadata
            except Exception as e:
                logger.warning("Web scan failed in comprehensive scan", error=str(e))
        
        # SSL/TLS scan
        if self.ssl_scanner and "://" in request.target:
            try:
                ssl_request = ScanRequest(
                    target=request.target,
                    scan_type=ScanType.SSL_TLS,
                    profile=request.profile,
                    options=request.options
                )
                ssl_result = await asyncio.wait_for(
                    self.ssl_scanner.scan(ssl_request),
                    timeout=timeout // 4
                )
                all_findings.extend(ssl_result.findings)
                scan_details["ssl"] = ssl_result.scan_metadata
            except Exception as e:
                logger.warning("SSL scan failed in comprehensive scan", error=str(e))
        
        # Vulnerability scan
        if self.vulnerability_scanner:
            try:
                vuln_request = ScanRequest(
                    target=request.target,
                    scan_type=ScanType.VULNERABILITY,
                    profile=request.profile,
                    options=request.options
                )
                vuln_result = await asyncio.wait_for(
                    self.vulnerability_scanner.scan(vuln_request),
                    timeout=timeout // 4
                )
                all_findings.extend(vuln_result.findings)
                scan_details["vulnerability"] = vuln_result.scan_metadata
            except Exception as e:
                logger.warning("Vulnerability scan failed in comprehensive scan", error=str(e))
        
        # Create comprehensive result
        result = ScanResult(
            scan_id=str(uuid.uuid4()),
            target=request.target,
            scan_type=ScanType.COMPREHENSIVE,
            status=ScanStatus.COMPLETED,
            timestamp=datetime.utcnow(),
            findings=all_findings,
            scan_metadata={
                "comprehensive_scan": True,
                "sub_scans": scan_details,
                "total_findings": len(all_findings)
            }
        )
        
        return result
    
    def _update_scan_statistics(self, result: ScanResult, execution_time: float) -> None:
        """Update scan statistics."""
        # Count vulnerabilities by severity
        high_severity_count = sum(
            1 for finding in result.findings
            if finding.severity in [VulnerabilityLevel.HIGH, VulnerabilityLevel.CRITICAL]
        )
        
        self.stats["vulnerabilities_found"] += len(result.findings)
        self.stats["high_severity_findings"] += high_severity_count
        self.stats["last_scan"] = datetime.utcnow()
        
        # Update average scan time
        total_scans = self.stats["scans_completed"] + 1
        current_avg = self.stats["average_scan_time"]
        self.stats["average_scan_time"] = (current_avg * (total_scans - 1) + execution_time) / total_scans
    
    async def start_scan(self, request: ScanRequest) -> str:
        """Start a new security scan."""
        try:
            # Validate target
            self._validate_scan_target(request.target)
            
            # Check rate limits
            await self._check_rate_limits(request)
            
            # Generate scan ID
            scan_id = str(uuid.uuid4())
            
            # Create scan entry
            self.active_scans[scan_id] = {
                "scan_id": scan_id,
                "request": request,
                "state": ScanState.QUEUED,
                "created_at": datetime.utcnow(),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None
            }
            
            # Add to queue
            scan_data = {
                "scan_id": scan_id,
                "request": request
            }
            
            await self.scan_queue.put(scan_data)
            
            logger.info(
                "Scan queued",
                scan_id=scan_id,
                scan_type=request.scan_type.value,
                target=request.target
            )
            
            return scan_id
            
        except Exception as e:
            logger.error("Failed to start scan", error=str(e))
            raise ScanExecutionError(f"Failed to start scan: {str(e)}")
    
    def _validate_scan_target(self, target: str) -> None:
        """Validate scan target against allowed/blocked networks."""
        import ipaddress
        
        # Extract IP from target if it's a URL
        if "://" in target:
            from urllib.parse import urlparse
            parsed = urlparse(target)
            hostname = parsed.hostname
            if not hostname:
                raise InvalidTargetError(target, "Cannot extract hostname from URL")
            
            # Try to resolve to IP
            try:
                import socket
                ip = socket.gethostbyname(hostname)
            except socket.gaierror:
                raise InvalidTargetError(target, "Cannot resolve hostname to IP")
        else:
            # Assume it's an IP or network range
            ip = target.split('/')[0]  # Handle CIDR notation
        
        try:
            ip_addr = ipaddress.ip_address(ip)
        except ValueError:
            raise InvalidTargetError(target, "Invalid IP address format")
        
        # Check against blocked networks
        for blocked_network in self.settings.blocked_target_networks:
            if ip_addr in ipaddress.ip_network(blocked_network, strict=False):
                raise InvalidTargetError(target, f"Target in blocked network: {blocked_network}")
        
        # Check against allowed networks
        allowed = False
        for allowed_network in self.settings.allowed_target_networks:
            if ip_addr in ipaddress.ip_network(allowed_network, strict=False):
                allowed = True
                break
        
        if not allowed:
            raise InvalidTargetError(target, "Target not in allowed networks")
    
    async def _check_rate_limits(self, request: ScanRequest) -> None:
        """Check if scan request exceeds rate limits."""
        if not self.settings.rate_limit_enabled:
            return
        
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        
        # Clean old entries
        key = "global"  # Could be per-user in the future
        if key not in self.scan_count_per_hour:
            self.scan_count_per_hour[key] = []
        
        self.scan_count_per_hour[key] = [
            timestamp for timestamp in self.scan_count_per_hour[key]
            if timestamp > hour_ago
        ]
        
        # Check limit
        if len(self.scan_count_per_hour[key]) >= self.settings.scans_per_hour:
            raise ScanLimitExceededError(self.settings.scans_per_hour, "hour")
        
        # Add current request
        self.scan_count_per_hour[key].append(current_time)
    
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Get status of a specific scan."""
        if scan_id not in self.active_scans:
            # Check scan history
            for scan in self.scan_history:
                if scan["scan_id"] == scan_id:
                    return scan
            raise ResourceNotFoundError("scan", scan_id)
        
        return self.active_scans[scan_id]
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """Cancel a running scan."""
        if scan_id not in self.active_scans:
            raise ResourceNotFoundError("scan", scan_id)
        
        scan = self.active_scans[scan_id]
        
        if scan["state"] in [ScanState.COMPLETED, ScanState.FAILED, ScanState.CANCELLED]:
            return False
        
        scan["state"] = ScanState.CANCELLED
        scan["completed_at"] = datetime.utcnow()
        
        logger.info("Scan cancelled", scan_id=scan_id)
        return True
    
    async def get_active_scans(self) -> List[Dict[str, Any]]:
        """Get list of active scans."""
        return [
            scan for scan in self.active_scans.values()
            if scan["state"] in [ScanState.QUEUED, ScanState.RUNNING]
        ]
    
    async def generate_report(self, scan_id: str, format_type: str) -> str:
        """Generate report for a completed scan."""
        if scan_id not in self.active_scans:
            raise ResourceNotFoundError("scan", scan_id)
        
        scan = self.active_scans[scan_id]
        
        if scan["state"] != ScanState.COMPLETED or not scan["result"]:
            raise ScanExecutionError("Cannot generate report for incomplete scan")
        
        if not self.report_generator:
            raise ScanExecutionError("Report generator not available")
        
        return await self.report_generator.generate_report(scan["result"], format_type)
    
    async def _cleanup_task(self) -> None:
        """Background task for cleaning up old scans."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(days=1)
                
                # Move old scans to history
                to_remove = []
                for scan_id, scan in self.active_scans.items():
                    if (scan["completed_at"] and scan["completed_at"] < cutoff_time) or \
                       (scan["created_at"] < cutoff_time and scan["state"] == ScanState.QUEUED):
                        self.scan_history.append(scan)
                        to_remove.append(scan_id)
                
                for scan_id in to_remove:
                    del self.active_scans[scan_id]
                
                # Limit history size
                if len(self.scan_history) > 1000:
                    self.scan_history = self.scan_history[-1000:]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error("Error in cleanup task", error=str(e))
                await asyncio.sleep(3600)
    
    async def _stats_update_task(self) -> None:
        """Background task for updating statistics."""
        while self._running:
            try:
                # Update statistics
                logger.debug(
                    "Scan orchestrator stats",
                    active_scans=len(self.active_scans),
                    queue_size=self.scan_queue.qsize(),
                    **self.stats
                )
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error("Error in stats update task", error=str(e))
                await asyncio.sleep(300)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get scan orchestrator statistics."""
        return {
            **self.stats,
            "active_scans": len(self.active_scans),
            "queue_size": self.scan_queue.qsize(),
            "scan_history_size": len(self.scan_history),
            "engines_status": {
                "network": self.network_scanner is not None,
                "web": self.web_scanner is not None,
                "vulnerability": self.vulnerability_scanner is not None,
                "ssl": self.ssl_scanner is not None,
                "infrastructure": self.infrastructure_scanner is not None
            }
        }
    
    async def cleanup(self) -> None:
        """Cleanup scan orchestrator resources."""
        try:
            self._running = False
            
            # Cancel background tasks
            for task in self._tasks:
                task.cancel()
            
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Cleanup scanners
            if self.network_scanner:
                await self.network_scanner.cleanup()
            
            if self.web_scanner:
                await self.web_scanner.cleanup()
            
            if self.vulnerability_scanner:
                await self.vulnerability_scanner.cleanup()
            
            if self.ssl_scanner:
                await self.ssl_scanner.cleanup()
            
            if self.infrastructure_scanner:
                await self.infrastructure_scanner.cleanup()
            
            logger.info("Scan orchestrator cleanup completed")
            
        except Exception as e:
            logger.error("Error during scan orchestrator cleanup", error=str(e))