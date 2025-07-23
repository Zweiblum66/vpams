"""
Security Scanner Module - Core scanning functionality
"""

import asyncio
import json
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
import structlog
from pathlib import Path
import tempfile

from .config import Settings

logger = structlog.get_logger()


class SecurityScanner:
    """Base security scanner interface"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def scan(self, target: str) -> Dict[str, Any]:
        """Run security scan on target"""
        raise NotImplementedError


class CodeScanner(SecurityScanner):
    """Static code analysis scanner using Bandit and Semgrep"""
    
    async def scan(self, target: str) -> Dict[str, Any]:
        """Scan code for security vulnerabilities"""
        results = {
            "scanner": "code",
            "target": target,
            "timestamp": datetime.utcnow().isoformat(),
            "findings": []
        }
        
        # Run Bandit scan
        bandit_results = await self._run_bandit(target)
        results["findings"].extend(bandit_results)
        
        # Run Semgrep scan
        semgrep_results = await self._run_semgrep(target)
        results["findings"].extend(semgrep_results)
        
        results["summary"] = {
            "total": len(results["findings"]),
            "critical": sum(1 for f in results["findings"] if f["severity"] == "critical"),
            "high": sum(1 for f in results["findings"] if f["severity"] == "high"),
            "medium": sum(1 for f in results["findings"] if f["severity"] == "medium"),
            "low": sum(1 for f in results["findings"] if f["severity"] == "low")
        }
        
        return results
    
    async def _run_bandit(self, target: str) -> List[Dict[str, Any]]:
        """Run Bandit security scanner"""
        try:
            cmd = ["bandit", "-r", target, "-f", "json", "-ll"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode not in [0, 1]:  # Bandit returns 1 if issues found
                logger.error("Bandit scan failed", stderr=stderr.decode())
                return []
            
            results = json.loads(stdout.decode())
            findings = []
            
            for result in results.get("results", []):
                findings.append({
                    "type": "code_vulnerability",
                    "scanner": "bandit",
                    "severity": self._map_bandit_severity(result["issue_severity"]),
                    "confidence": result["issue_confidence"],
                    "title": result["issue_text"],
                    "description": result["more_info"],
                    "file": result["filename"],
                    "line": result["line_number"],
                    "code": result["code"],
                    "test_id": result["test_id"],
                    "test_name": result["test_name"]
                })
            
            return findings
            
        except Exception as e:
            logger.error("Bandit scan error", error=str(e))
            return []
    
    async def _run_semgrep(self, target: str) -> List[Dict[str, Any]]:
        """Run Semgrep security scanner"""
        try:
            cmd = ["semgrep", "--config=auto", "--json", target]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error("Semgrep scan failed", stderr=stderr.decode())
                return []
            
            results = json.loads(stdout.decode())
            findings = []
            
            for result in results.get("results", []):
                findings.append({
                    "type": "code_vulnerability",
                    "scanner": "semgrep",
                    "severity": self._map_semgrep_severity(result.get("extra", {}).get("severity", "INFO")),
                    "confidence": "high",
                    "title": result.get("extra", {}).get("message", "Security issue found"),
                    "description": result.get("extra", {}).get("metadata", {}).get("description", ""),
                    "file": result["path"],
                    "line": result["start"]["line"],
                    "code": result.get("extra", {}).get("lines", ""),
                    "rule_id": result["check_id"],
                    "owasp": result.get("extra", {}).get("metadata", {}).get("owasp", [])
                })
            
            return findings
            
        except Exception as e:
            logger.error("Semgrep scan error", error=str(e))
            return []
    
    def _map_bandit_severity(self, severity: str) -> str:
        """Map Bandit severity to standard levels"""
        mapping = {
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low"
        }
        return mapping.get(severity.upper(), "low")
    
    def _map_semgrep_severity(self, severity: str) -> str:
        """Map Semgrep severity to standard levels"""
        mapping = {
            "ERROR": "critical",
            "WARNING": "high",
            "INFO": "medium",
            "INVENTORY": "low"
        }
        return mapping.get(severity.upper(), "medium")


class DependencyScanner(SecurityScanner):
    """Dependency vulnerability scanner using Safety and pip-audit"""
    
    async def scan(self, target: str) -> Dict[str, Any]:
        """Scan dependencies for known vulnerabilities"""
        results = {
            "scanner": "dependency",
            "target": target,
            "timestamp": datetime.utcnow().isoformat(),
            "findings": []
        }
        
        # Find requirements files
        req_files = self._find_requirements_files(target)
        
        for req_file in req_files:
            # Run Safety scan
            safety_results = await self._run_safety(req_file)
            results["findings"].extend(safety_results)
            
            # Run pip-audit scan
            audit_results = await self._run_pip_audit(req_file)
            results["findings"].extend(audit_results)
        
        results["summary"] = {
            "total": len(results["findings"]),
            "critical": sum(1 for f in results["findings"] if f["severity"] == "critical"),
            "high": sum(1 for f in results["findings"] if f["severity"] == "high"),
            "medium": sum(1 for f in results["findings"] if f["severity"] == "medium"),
            "low": sum(1 for f in results["findings"] if f["severity"] == "low")
        }
        
        return results
    
    def _find_requirements_files(self, target: str) -> List[str]:
        """Find all requirements files in target directory"""
        path = Path(target)
        patterns = ["requirements*.txt", "Pipfile", "pyproject.toml", "package.json", "package-lock.json"]
        files = []
        
        for pattern in patterns:
            files.extend(path.rglob(pattern))
        
        return [str(f) for f in files]
    
    async def _run_safety(self, req_file: str) -> List[Dict[str, Any]]:
        """Run Safety dependency scanner"""
        try:
            cmd = ["safety", "check", "-r", req_file, "--json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode not in [0, 64]:  # Safety returns 64 if vulnerabilities found
                logger.error("Safety scan failed", stderr=stderr.decode())
                return []
            
            results = json.loads(stdout.decode())
            findings = []
            
            for vuln in results.get("vulnerabilities", []):
                findings.append({
                    "type": "dependency_vulnerability",
                    "scanner": "safety",
                    "severity": self._calculate_severity(vuln.get("vulnerability", {}).get("cvss_score", 0)),
                    "confidence": "high",
                    "title": f"Vulnerable dependency: {vuln['package_name']}",
                    "description": vuln.get("vulnerability", {}).get("description", ""),
                    "package": vuln["package_name"],
                    "installed_version": vuln["installed_version"],
                    "affected_versions": vuln.get("affected_versions", ""),
                    "cve": vuln.get("vulnerability", {}).get("cve", ""),
                    "cvss_score": vuln.get("vulnerability", {}).get("cvss_score", 0),
                    "advisory": vuln.get("vulnerability", {}).get("advisory", ""),
                    "file": req_file
                })
            
            return findings
            
        except Exception as e:
            logger.error("Safety scan error", error=str(e))
            return []
    
    async def _run_pip_audit(self, req_file: str) -> List[Dict[str, Any]]:
        """Run pip-audit dependency scanner"""
        try:
            cmd = ["pip-audit", "-r", req_file, "--format", "json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode not in [0, 1]:  # pip-audit returns 1 if vulnerabilities found
                logger.error("pip-audit scan failed", stderr=stderr.decode())
                return []
            
            results = json.loads(stdout.decode())
            findings = []
            
            for dep in results.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    findings.append({
                        "type": "dependency_vulnerability",
                        "scanner": "pip-audit",
                        "severity": self._calculate_severity(vuln.get("fix_versions", [])),
                        "confidence": "high",
                        "title": f"Vulnerable dependency: {dep['name']}",
                        "description": vuln.get("description", ""),
                        "package": dep["name"],
                        "installed_version": dep["version"],
                        "fix_versions": vuln.get("fix_versions", []),
                        "id": vuln.get("id", ""),
                        "file": req_file
                    })
            
            return findings
            
        except Exception as e:
            logger.error("pip-audit scan error", error=str(e))
            return []
    
    def _calculate_severity(self, cvss_score: float) -> str:
        """Calculate severity from CVSS score"""
        if isinstance(cvss_score, list):
            return "high"  # If fix versions exist, consider it high
        
        if cvss_score >= 9.0:
            return "critical"
        elif cvss_score >= 7.0:
            return "high"
        elif cvss_score >= 4.0:
            return "medium"
        else:
            return "low"


class WebScanner(SecurityScanner):
    """Web application scanner using OWASP ZAP"""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.zap_url = f"http://{settings.zap_proxy_host}:{settings.zap_proxy_port}"
    
    async def scan(self, target: str) -> Dict[str, Any]:
        """Scan web application for vulnerabilities"""
        results = {
            "scanner": "web",
            "target": target,
            "timestamp": datetime.utcnow().isoformat(),
            "findings": []
        }
        
        try:
            # Start spider scan
            await self._spider_scan(target)
            
            # Run active scan
            scan_id = await self._active_scan(target)
            
            # Wait for scan completion
            await self._wait_for_scan(scan_id)
            
            # Get results
            alerts = await self._get_alerts(target)
            
            for alert in alerts:
                results["findings"].append({
                    "type": "web_vulnerability",
                    "scanner": "owasp_zap",
                    "severity": self._map_zap_risk(alert["risk"]),
                    "confidence": alert["confidence"],
                    "title": alert["alert"],
                    "description": alert["description"],
                    "solution": alert["solution"],
                    "reference": alert["reference"],
                    "url": alert["url"],
                    "param": alert.get("param", ""),
                    "attack": alert.get("attack", ""),
                    "evidence": alert.get("evidence", ""),
                    "cwe_id": alert.get("cweid", ""),
                    "wasc_id": alert.get("wascid", "")
                })
            
        except Exception as e:
            logger.error("Web scan error", error=str(e))
        
        results["summary"] = {
            "total": len(results["findings"]),
            "critical": sum(1 for f in results["findings"] if f["severity"] == "critical"),
            "high": sum(1 for f in results["findings"] if f["severity"] == "high"),
            "medium": sum(1 for f in results["findings"] if f["severity"] == "medium"),
            "low": sum(1 for f in results["findings"] if f["severity"] == "low")
        }
        
        return results
    
    async def _spider_scan(self, target: str) -> None:
        """Run spider scan to discover URLs"""
        async with aiohttp.ClientSession() as session:
            params = {
                "url": target,
                "maxChildren": 10,
                "recurse": True
            }
            if self.settings.zap_api_key:
                params["apikey"] = self.settings.zap_api_key
            
            async with session.get(f"{self.zap_url}/JSON/spider/action/scan/", params=params) as resp:
                data = await resp.json()
                scan_id = data["scan"]
            
            # Wait for spider to complete
            while True:
                params = {"scanId": scan_id}
                if self.settings.zap_api_key:
                    params["apikey"] = self.settings.zap_api_key
                
                async with session.get(f"{self.zap_url}/JSON/spider/view/status/", params=params) as resp:
                    data = await resp.json()
                    if int(data["status"]) >= 100:
                        break
                
                await asyncio.sleep(2)
    
    async def _active_scan(self, target: str) -> str:
        """Run active vulnerability scan"""
        async with aiohttp.ClientSession() as session:
            params = {
                "url": target,
                "recurse": True,
                "inScopeOnly": False
            }
            if self.settings.zap_api_key:
                params["apikey"] = self.settings.zap_api_key
            
            async with session.get(f"{self.zap_url}/JSON/ascan/action/scan/", params=params) as resp:
                data = await resp.json()
                return data["scan"]
    
    async def _wait_for_scan(self, scan_id: str) -> None:
        """Wait for active scan to complete"""
        async with aiohttp.ClientSession() as session:
            while True:
                params = {"scanId": scan_id}
                if self.settings.zap_api_key:
                    params["apikey"] = self.settings.zap_api_key
                
                async with session.get(f"{self.zap_url}/JSON/ascan/view/status/", params=params) as resp:
                    data = await resp.json()
                    if int(data["status"]) >= 100:
                        break
                
                await asyncio.sleep(5)
    
    async def _get_alerts(self, target: str) -> List[Dict[str, Any]]:
        """Get scan alerts"""
        async with aiohttp.ClientSession() as session:
            params = {"baseurl": target}
            if self.settings.zap_api_key:
                params["apikey"] = self.settings.zap_api_key
            
            async with session.get(f"{self.zap_url}/JSON/alert/view/alerts/", params=params) as resp:
                data = await resp.json()
                return data.get("alerts", [])
    
    def _map_zap_risk(self, risk: str) -> str:
        """Map ZAP risk levels to standard severity"""
        mapping = {
            "High": "high",
            "Medium": "medium",
            "Low": "low",
            "Informational": "info"
        }
        return mapping.get(risk, "low")