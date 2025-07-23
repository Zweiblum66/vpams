"""Scanner Service - Orchestrates various security scanners"""

import asyncio
import os
import json
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import tempfile
import structlog

from src.core.config import settings
from src.models.schemas import (
    ScanType, SeverityLevel, Finding, ComplianceStandard,
    ComplianceRequirement, ComplianceControl
)

logger = structlog.get_logger()


class ScannerService:
    """Service for orchestrating security scans"""
    
    def __init__(self):
        """Initialize scanner service"""
        self.scanner_configs = {
            ScanType.CODE: {
                "tools": ["bandit", "semgrep"],
                "enabled": True
            },
            ScanType.DEPENDENCY: {
                "tools": ["safety", "pip-audit"],
                "enabled": True
            },
            ScanType.WEB: {
                "tools": ["zap"],
                "enabled": settings.owasp_top_10_enabled
            },
            ScanType.NETWORK: {
                "tools": ["nmap"],
                "enabled": settings.network_scan_enabled
            },
            ScanType.COMPLIANCE: {
                "tools": ["compliance-checker"],
                "enabled": True
            }
        }
    
    async def run_scan(
        self,
        scan_type: ScanType,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run a security scan of the specified type"""
        try:
            logger.info(f"Starting {scan_type.value} scan", target=target)
            
            if scan_type == ScanType.CODE:
                return await self._run_code_scan(target, options)
            elif scan_type == ScanType.DEPENDENCY:
                return await self._run_dependency_scan(target, options)
            elif scan_type == ScanType.WEB:
                return await self._run_web_scan(target, options)
            elif scan_type == ScanType.NETWORK:
                return await self._run_network_scan(target, options)
            else:
                logger.warning(f"Unsupported scan type: {scan_type.value}")
                return []
                
        except Exception as e:
            logger.error(f"Scan failed for {scan_type.value}", error=str(e))
            raise
    
    async def _run_code_scan(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run code security scan using Bandit and Semgrep"""
        findings = []
        
        # Run Bandit scan
        if "bandit" in self.scanner_configs[ScanType.CODE]["tools"]:
            bandit_findings = await self._run_bandit(target, options)
            findings.extend(bandit_findings)
        
        # Run Semgrep scan
        if "semgrep" in self.scanner_configs[ScanType.CODE]["tools"]:
            semgrep_findings = await self._run_semgrep(target, options)
            findings.extend(semgrep_findings)
        
        return findings
    
    async def _run_bandit(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run Bandit security scanner"""
        findings = []
        
        try:
            # Prepare Bandit command
            cmd = [
                "bandit",
                "-r", target,
                "-f", "json",
                "--severity-level", "low"
            ]
            
            # Add exclude patterns if provided
            if options and "exclude_patterns" in options:
                for pattern in options["exclude_patterns"]:
                    cmd.extend(["-x", pattern])
            
            # Run Bandit
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode not in [0, 1]:  # Bandit returns 1 if issues found
                logger.error("Bandit scan failed", stderr=stderr.decode())
                return findings
            
            # Parse Bandit output
            bandit_results = json.loads(stdout.decode())
            
            for issue in bandit_results.get("results", []):
                finding = Finding(
                    type="code_vulnerability",
                    scanner="bandit",
                    severity=self._map_bandit_severity(issue["issue_severity"]),
                    confidence=issue["issue_confidence"],
                    title=f"{issue['test_id']}: {issue['test_name']}",
                    description=issue["issue_text"],
                    file=issue["filename"],
                    line=issue["line_number"],
                    cwe_id=f"CWE-{issue.get('issue_cwe', {}).get('id', 'unknown')}",
                    solution=issue.get("more_info", "Review and fix the security issue")
                )
                findings.append(finding)
            
            logger.info(f"Bandit scan completed", findings_count=len(findings))
            
        except Exception as e:
            logger.error("Bandit scan error", error=str(e))
        
        return findings
    
    async def _run_semgrep(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run Semgrep security scanner"""
        findings = []
        
        try:
            # Prepare Semgrep command
            cmd = [
                "semgrep",
                "--config=auto",
                "--json",
                "--no-error",
                target
            ]
            
            # Run Semgrep
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error("Semgrep scan failed", stderr=stderr.decode())
                return findings
            
            # Parse Semgrep output
            semgrep_results = json.loads(stdout.decode())
            
            for issue in semgrep_results.get("results", []):
                finding = Finding(
                    type="code_vulnerability",
                    scanner="semgrep",
                    severity=self._map_semgrep_severity(issue.get("extra", {}).get("severity", "INFO")),
                    confidence="high",
                    title=issue.get("check_id", "Unknown rule"),
                    description=issue.get("extra", {}).get("message", "Security issue detected"),
                    file=issue["path"],
                    line=issue["start"]["line"],
                    owasp=issue.get("extra", {}).get("metadata", {}).get("owasp", []),
                    solution=issue.get("extra", {}).get("fix", "Review and fix the security issue"),
                    references=issue.get("extra", {}).get("metadata", {}).get("references", [])
                )
                findings.append(finding)
            
            logger.info(f"Semgrep scan completed", findings_count=len(findings))
            
        except Exception as e:
            logger.error("Semgrep scan error", error=str(e))
        
        return findings
    
    async def _run_dependency_scan(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run dependency vulnerability scan"""
        findings = []
        
        # Find requirements files
        req_files = []
        for root, dirs, files in os.walk(target):
            for file in files:
                if file in ["requirements.txt", "requirements.in", "Pipfile", "poetry.lock"]:
                    req_files.append(os.path.join(root, file))
        
        # Run Safety check
        for req_file in req_files:
            safety_findings = await self._run_safety(req_file, options)
            findings.extend(safety_findings)
        
        return findings
    
    async def _run_safety(
        self,
        req_file: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run Safety dependency scanner"""
        findings = []
        
        try:
            # Prepare Safety command
            cmd = [
                "safety", "check",
                "--file", req_file,
                "--json"
            ]
            
            # Run Safety
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            # Safety returns non-zero if vulnerabilities found
            if stdout:
                safety_results = json.loads(stdout.decode())
                
                for vuln in safety_results.get("vulnerabilities", []):
                    finding = Finding(
                        type="dependency_vulnerability",
                        scanner="safety",
                        severity=self._map_safety_severity(vuln.get("severity", "unknown")),
                        confidence="high",
                        title=f"{vuln['package']} {vuln['affected_versions']}",
                        description=vuln["description"],
                        file=req_file,
                        cve=vuln.get("cve"),
                        cvss_score=vuln.get("cvss"),
                        solution=f"Update {vuln['package']} to {vuln.get('fixed_versions', 'latest secure version')}",
                        references=[vuln.get("advisory")]
                    )
                    findings.append(finding)
            
            logger.info(f"Safety scan completed for {req_file}", findings_count=len(findings))
            
        except Exception as e:
            logger.error("Safety scan error", error=str(e))
        
        return findings
    
    async def _run_web_scan(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run web application security scan"""
        findings = []
        
        # This would integrate with OWASP ZAP or similar
        # For now, return mock OWASP findings
        
        owasp_checks = [
            {
                "category": "injection",
                "title": "SQL Injection",
                "description": "Potential SQL injection vulnerability detected",
                "severity": "high"
            },
            {
                "category": "broken_authentication",
                "title": "Weak Password Policy",
                "description": "Password policy does not meet security standards",
                "severity": "medium"
            },
            {
                "category": "sensitive_data_exposure",
                "title": "Unencrypted Data Transmission",
                "description": "Sensitive data transmitted without encryption",
                "severity": "high"
            }
        ]
        
        for check in owasp_checks:
            if await self._simulate_vulnerability_check():
                finding = Finding(
                    type="web_vulnerability",
                    scanner="owasp_zap",
                    severity=SeverityLevel(check["severity"]),
                    confidence="medium",
                    title=check["title"],
                    description=check["description"],
                    url=target,
                    owasp=[check["category"]],
                    solution="Implement proper security controls"
                )
                findings.append(finding)
        
        return findings
    
    async def _run_network_scan(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """Run network security scan"""
        findings = []
        
        try:
            # Basic port scan
            cmd = [
                "nmap",
                "-sV",  # Version detection
                "-O",   # OS detection
                "--script", "vuln",  # Vulnerability scripts
                "-oX", "-",  # XML output to stdout
                target
            ]
            
            # Run nmap
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error("Nmap scan failed", stderr=stderr.decode())
                return findings
            
            # Parse nmap output (simplified)
            # In production, would parse XML output properly
            output = stdout.decode()
            
            # Check for common issues
            if "open" in output and "ssh" in output.lower():
                finding = Finding(
                    type="network_vulnerability",
                    scanner="nmap",
                    severity=SeverityLevel.MEDIUM,
                    confidence="high",
                    title="SSH Service Exposed",
                    description="SSH service is accessible from the network",
                    url=f"{target}:22",
                    solution="Restrict SSH access to trusted networks only"
                )
                findings.append(finding)
            
            logger.info(f"Network scan completed", findings_count=len(findings))
            
        except Exception as e:
            logger.error("Network scan error", error=str(e))
        
        return findings
    
    async def check_compliance(
        self,
        standard: ComplianceStandard,
        target: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[ComplianceControl]:
        """Check compliance with security standards"""
        controls = []
        
        # Get compliance requirements for the standard
        requirements = self._get_compliance_requirements(standard)
        
        for control_id, control_data in requirements.items():
            control_requirements = []
            
            for req in control_data["requirements"]:
                # Check each requirement
                status = await self._check_requirement(req, target)
                
                control_requirements.append(
                    ComplianceRequirement(
                        id=req["id"],
                        description=req["description"],
                        status=status,
                        evidence=f"Checked on {datetime.utcnow().isoformat()}",
                        severity=SeverityLevel.HIGH if status == "fail" else None
                    )
                )
            
            # Calculate control score
            passed = sum(1 for r in control_requirements if r.status == "pass")
            total = len(control_requirements)
            score = (passed / total) if total > 0 else 0.0
            
            controls.append(
                ComplianceControl(
                    id=control_id,
                    name=control_data["name"],
                    requirements=control_requirements,
                    score=score
                )
            )
        
        return controls
    
    def _get_compliance_requirements(
        self,
        standard: ComplianceStandard
    ) -> Dict[str, Any]:
        """Get compliance requirements for a standard"""
        # Simplified compliance requirements
        if standard == ComplianceStandard.ISO27001:
            return {
                "A.9.1": {
                    "name": "Access Control",
                    "requirements": [
                        {"id": "A.9.1.1", "description": "Access control policy"},
                        {"id": "A.9.1.2", "description": "Access to networks"}
                    ]
                },
                "A.12.1": {
                    "name": "Operational Security",
                    "requirements": [
                        {"id": "A.12.1.1", "description": "Documented procedures"},
                        {"id": "A.12.1.2", "description": "Change management"}
                    ]
                }
            }
        elif standard == ComplianceStandard.GDPR:
            return {
                "Art32": {
                    "name": "Security of Processing",
                    "requirements": [
                        {"id": "32.1.a", "description": "Pseudonymization and encryption"},
                        {"id": "32.1.b", "description": "Confidentiality and integrity"}
                    ]
                }
            }
        else:
            return {}
    
    async def _check_requirement(
        self,
        requirement: Dict[str, str],
        target: str
    ) -> str:
        """Check a specific compliance requirement"""
        # Simplified compliance checking
        # In production, would perform actual checks
        
        if "encryption" in requirement["description"].lower():
            # Check for encryption
            return "pass"  # Assume encryption is implemented
        elif "access" in requirement["description"].lower():
            # Check access controls
            return "pass"  # Assume access controls exist
        else:
            # Random check for demo
            import random
            return "pass" if random.random() > 0.2 else "fail"
    
    async def _simulate_vulnerability_check(self) -> bool:
        """Simulate vulnerability detection for demo"""
        import random
        return random.random() > 0.7
    
    def _map_bandit_severity(self, severity: str) -> SeverityLevel:
        """Map Bandit severity to our severity levels"""
        mapping = {
            "HIGH": SeverityLevel.HIGH,
            "MEDIUM": SeverityLevel.MEDIUM,
            "LOW": SeverityLevel.LOW
        }
        return mapping.get(severity.upper(), SeverityLevel.INFO)
    
    def _map_semgrep_severity(self, severity: str) -> SeverityLevel:
        """Map Semgrep severity to our severity levels"""
        mapping = {
            "ERROR": SeverityLevel.HIGH,
            "WARNING": SeverityLevel.MEDIUM,
            "INFO": SeverityLevel.LOW
        }
        return mapping.get(severity.upper(), SeverityLevel.INFO)
    
    def _map_safety_severity(self, severity: str) -> SeverityLevel:
        """Map Safety severity to our severity levels"""
        # Safety doesn't provide severity, so map based on CVSS score
        return SeverityLevel.HIGH  # Conservative default