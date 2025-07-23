"""
Compliance Checker Module - ISO 27001, GDPR, SOC2 compliance verification
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import structlog
import re

from .config import Settings

logger = structlog.get_logger()


class ComplianceChecker:
    """Base compliance checker interface"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def check(self, target: str) -> Dict[str, Any]:
        """Run compliance check"""
        raise NotImplementedError


class ISO27001Checker(ComplianceChecker):
    """ISO 27001 Information Security Management compliance checker"""
    
    async def check(self, target: str) -> Dict[str, Any]:
        """Check ISO 27001 compliance"""
        results = {
            "standard": "ISO 27001",
            "target": target,
            "timestamp": datetime.utcnow().isoformat(),
            "controls": [],
            "score": 0
        }
        
        # Check information security controls
        controls = [
            await self._check_access_control(target),
            await self._check_cryptography(target),
            await self._check_security_operations(target),
            await self._check_communication_security(target),
            await self._check_system_acquisition(target),
            await self._check_incident_management(target),
            await self._check_business_continuity(target),
            await self._check_supplier_relationships(target)
        ]
        
        results["controls"] = controls
        results["score"] = sum(c["score"] for c in controls) / len(controls)
        results["status"] = "compliant" if results["score"] >= 0.8 else "non_compliant"
        
        return results
    
    async def _check_access_control(self, target: str) -> Dict[str, Any]:
        """A.9 Access Control"""
        control = {
            "id": "A.9",
            "name": "Access Control",
            "requirements": [],
            "score": 0
        }
        
        # Check for authentication mechanisms
        auth_found = await self._scan_for_patterns(target, [
            r"@login_required",
            r"authenticate",
            r"jwt\.decode",
            r"password.*hash",
            r"OAuth",
            r"LDAP"
        ])
        
        control["requirements"].append({
            "id": "A.9.1.1",
            "description": "Access control policy",
            "status": "pass" if auth_found else "fail",
            "evidence": f"Authentication patterns found: {len(auth_found)}"
        })
        
        # Check for role-based access control
        rbac_found = await self._scan_for_patterns(target, [
            r"@require_role",
            r"permissions",
            r"has_permission",
            r"user_roles",
            r"check_access"
        ])
        
        control["requirements"].append({
            "id": "A.9.2.1",
            "description": "User access provisioning",
            "status": "pass" if rbac_found else "fail",
            "evidence": f"RBAC patterns found: {len(rbac_found)}"
        })
        
        # Check for privileged access management
        pam_found = await self._scan_for_patterns(target, [
            r"admin_required",
            r"superuser",
            r"privilege.*escalation",
            r"sudo",
            r"admin.*check"
        ])
        
        control["requirements"].append({
            "id": "A.9.2.3",
            "description": "Management of privileged access rights",
            "status": "pass" if pam_found else "fail",
            "evidence": f"PAM patterns found: {len(pam_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _check_cryptography(self, target: str) -> Dict[str, Any]:
        """A.10 Cryptography"""
        control = {
            "id": "A.10",
            "name": "Cryptography",
            "requirements": [],
            "score": 0
        }
        
        # Check for encryption usage
        crypto_found = await self._scan_for_patterns(target, [
            r"encrypt",
            r"decrypt",
            r"AES",
            r"RSA",
            r"cryptography",
            r"hashlib",
            r"bcrypt",
            r"scrypt"
        ])
        
        control["requirements"].append({
            "id": "A.10.1.1",
            "description": "Policy on the use of cryptographic controls",
            "status": "pass" if crypto_found else "fail",
            "evidence": f"Cryptographic patterns found: {len(crypto_found)}"
        })
        
        # Check for key management
        key_mgmt_found = await self._scan_for_patterns(target, [
            r"key.*management",
            r"key.*rotation",
            r"private.*key",
            r"public.*key",
            r"secret.*key"
        ])
        
        control["requirements"].append({
            "id": "A.10.1.2",
            "description": "Key management",
            "status": "pass" if key_mgmt_found else "fail",
            "evidence": f"Key management patterns found: {len(key_mgmt_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _check_security_operations(self, target: str) -> Dict[str, Any]:
        """A.12 Operations Security"""
        control = {
            "id": "A.12",
            "name": "Operations Security",
            "requirements": [],
            "score": 0
        }
        
        # Check for logging and monitoring
        logging_found = await self._scan_for_patterns(target, [
            r"logger\.",
            r"log\.",
            r"audit.*log",
            r"security.*event",
            r"monitoring",
            r"structlog"
        ])
        
        control["requirements"].append({
            "id": "A.12.4.1",
            "description": "Event logging",
            "status": "pass" if logging_found else "fail",
            "evidence": f"Logging patterns found: {len(logging_found)}"
        })
        
        # Check for vulnerability management
        vuln_mgmt_found = await self._scan_for_patterns(target, [
            r"vulnerability",
            r"security.*scan",
            r"penetration.*test",
            r"security.*assessment"
        ])
        
        control["requirements"].append({
            "id": "A.12.6.1",
            "description": "Management of technical vulnerabilities",
            "status": "pass" if vuln_mgmt_found else "fail",
            "evidence": f"Vulnerability management patterns found: {len(vuln_mgmt_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _check_communication_security(self, target: str) -> Dict[str, Any]:
        """A.13 Communications Security"""
        control = {
            "id": "A.13",
            "name": "Communications Security",
            "requirements": [],
            "score": 0
        }
        
        # Check for network security controls
        network_sec_found = await self._scan_for_patterns(target, [
            r"https://",
            r"ssl",
            r"tls",
            r"certificate",
            r"secure.*communication"
        ])
        
        control["requirements"].append({
            "id": "A.13.1.1",
            "description": "Network controls",
            "status": "pass" if network_sec_found else "fail",
            "evidence": f"Network security patterns found: {len(network_sec_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _check_system_acquisition(self, target: str) -> Dict[str, Any]:
        """A.14 System Acquisition, Development and Maintenance"""
        control = {
            "id": "A.14",
            "name": "System Acquisition, Development and Maintenance",
            "requirements": [],
            "score": 0
        }
        
        # Check for secure development practices
        secure_dev_found = await self._scan_for_patterns(target, [
            r"input.*validation",
            r"sanitize",
            r"escape",
            r"sql.*injection",
            r"xss.*protection",
            r"csrf.*token"
        ])
        
        control["requirements"].append({
            "id": "A.14.2.1",
            "description": "Secure development policy",
            "status": "pass" if secure_dev_found else "fail",
            "evidence": f"Secure development patterns found: {len(secure_dev_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _check_incident_management(self, target: str) -> Dict[str, Any]:
        """A.16 Information Security Incident Management"""
        control = {
            "id": "A.16",
            "name": "Information Security Incident Management",
            "requirements": [],
            "score": 0
        }
        
        # Check for incident response capabilities
        incident_found = await self._scan_for_patterns(target, [
            r"incident.*response",
            r"security.*incident",
            r"alert",
            r"notification",
            r"emergency.*response"
        ])
        
        control["requirements"].append({
            "id": "A.16.1.1",
            "description": "Responsibilities and procedures",
            "status": "pass" if incident_found else "fail",
            "evidence": f"Incident management patterns found: {len(incident_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _check_business_continuity(self, target: str) -> Dict[str, Any]:
        """A.17 Information Security Aspects of Business Continuity Management"""
        control = {
            "id": "A.17",
            "name": "Information Security Aspects of Business Continuity Management",
            "requirements": [],
            "score": 0
        }
        
        # Check for backup and recovery
        backup_found = await self._scan_for_patterns(target, [
            r"backup",
            r"recovery",
            r"disaster.*recovery",
            r"business.*continuity",
            r"failover"
        ])
        
        control["requirements"].append({
            "id": "A.17.1.2",
            "description": "Implementing information security continuity",
            "status": "pass" if backup_found else "fail",
            "evidence": f"Business continuity patterns found: {len(backup_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _check_supplier_relationships(self, target: str) -> Dict[str, Any]:
        """A.15 Supplier Relationships"""
        control = {
            "id": "A.15",
            "name": "Supplier Relationships",
            "requirements": [],
            "score": 0
        }
        
        # Check for supplier security
        supplier_found = await self._scan_for_patterns(target, [
            r"third.*party",
            r"vendor",
            r"supplier",
            r"api.*key",
            r"external.*service"
        ])
        
        control["requirements"].append({
            "id": "A.15.1.1",
            "description": "Information security policy for supplier relationships",
            "status": "pass" if supplier_found else "fail",
            "evidence": f"Supplier security patterns found: {len(supplier_found)}"
        })
        
        passed = sum(1 for req in control["requirements"] if req["status"] == "pass")
        control["score"] = passed / len(control["requirements"])
        
        return control
    
    async def _scan_for_patterns(self, target: str, patterns: List[str]) -> List[str]:
        """Scan for security patterns in code"""
        found = []
        path = Path(target)
        
        for file_path in path.rglob("*.py"):
            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        found.append(f"{file_path}:{pattern}")
            except Exception as e:
                logger.warning("Failed to scan file", file=str(file_path), error=str(e))
        
        return found


class GDPRChecker(ComplianceChecker):
    """GDPR (General Data Protection Regulation) compliance checker"""
    
    async def check(self, target: str) -> Dict[str, Any]:
        """Check GDPR compliance"""
        results = {
            "standard": "GDPR",
            "target": target,
            "timestamp": datetime.utcnow().isoformat(),
            "principles": [],
            "score": 0
        }
        
        principles = [
            await self._check_lawfulness(target),
            await self._check_purpose_limitation(target),
            await self._check_data_minimisation(target),
            await self._check_accuracy(target),
            await self._check_storage_limitation(target),
            await self._check_security(target),
            await self._check_accountability(target)
        ]
        
        results["principles"] = principles
        results["score"] = sum(p["score"] for p in principles) / len(principles)
        results["status"] = "compliant" if results["score"] >= 0.8 else "non_compliant"
        
        return results
    
    async def _check_lawfulness(self, target: str) -> Dict[str, Any]:
        """Check lawfulness, fairness and transparency"""
        principle = {
            "name": "Lawfulness, fairness and transparency",
            "requirements": [],
            "score": 0
        }
        
        # Check for consent management
        consent_found = await self._scan_for_patterns(target, [
            r"consent",
            r"agree.*terms",
            r"privacy.*policy",
            r"data.*processing.*agreement"
        ])
        
        principle["requirements"].append({
            "description": "Consent management",
            "status": "pass" if consent_found else "fail",
            "evidence": f"Consent patterns found: {len(consent_found)}"
        })
        
        passed = sum(1 for req in principle["requirements"] if req["status"] == "pass")
        principle["score"] = passed / len(principle["requirements"])
        
        return principle
    
    async def _check_purpose_limitation(self, target: str) -> Dict[str, Any]:
        """Check purpose limitation"""
        principle = {
            "name": "Purpose limitation",
            "requirements": [],
            "score": 0
        }
        
        # Check for data purpose documentation
        purpose_found = await self._scan_for_patterns(target, [
            r"purpose",
            r"data.*usage",
            r"processing.*purpose",
            r"why.*collect"
        ])
        
        principle["requirements"].append({
            "description": "Data processing purpose limitation",
            "status": "pass" if purpose_found else "fail",
            "evidence": f"Purpose limitation patterns found: {len(purpose_found)}"
        })
        
        passed = sum(1 for req in principle["requirements"] if req["status"] == "pass")
        principle["score"] = passed / len(principle["requirements"])
        
        return principle
    
    async def _check_data_minimisation(self, target: str) -> Dict[str, Any]:
        """Check data minimisation"""
        principle = {
            "name": "Data minimisation",
            "requirements": [],
            "score": 0
        }
        
        # Check for data collection limits
        minimisation_found = await self._scan_for_patterns(target, [
            r"data.*minimization",
            r"collect.*necessary",
            r"required.*fields",
            r"optional.*fields"
        ])
        
        principle["requirements"].append({
            "description": "Data minimisation practices",
            "status": "pass" if minimisation_found else "fail",
            "evidence": f"Data minimisation patterns found: {len(minimisation_found)}"
        })
        
        passed = sum(1 for req in principle["requirements"] if req["status"] == "pass")
        principle["score"] = passed / len(principle["requirements"])
        
        return principle
    
    async def _check_accuracy(self, target: str) -> Dict[str, Any]:
        """Check accuracy"""
        principle = {
            "name": "Accuracy",
            "requirements": [],
            "score": 0
        }
        
        # Check for data validation
        accuracy_found = await self._scan_for_patterns(target, [
            r"validation",
            r"verify",
            r"validate",
            r"data.*quality",
            r"accuracy"
        ])
        
        principle["requirements"].append({
            "description": "Data accuracy validation",
            "status": "pass" if accuracy_found else "fail",
            "evidence": f"Data accuracy patterns found: {len(accuracy_found)}"
        })
        
        passed = sum(1 for req in principle["requirements"] if req["status"] == "pass")
        principle["score"] = passed / len(principle["requirements"])
        
        return principle
    
    async def _check_storage_limitation(self, target: str) -> Dict[str, Any]:
        """Check storage limitation"""
        principle = {
            "name": "Storage limitation",
            "requirements": [],
            "score": 0
        }
        
        # Check for data retention policies
        retention_found = await self._scan_for_patterns(target, [
            r"retention",
            r"expiry",
            r"delete.*after",
            r"data.*lifecycle",
            r"purge"
        ])
        
        principle["requirements"].append({
            "description": "Data retention policies",
            "status": "pass" if retention_found else "fail",
            "evidence": f"Data retention patterns found: {len(retention_found)}"
        })
        
        passed = sum(1 for req in principle["requirements"] if req["status"] == "pass")
        principle["score"] = passed / len(principle["requirements"])
        
        return principle
    
    async def _check_security(self, target: str) -> Dict[str, Any]:
        """Check integrity and confidentiality"""
        principle = {
            "name": "Integrity and confidentiality",
            "requirements": [],
            "score": 0
        }
        
        # Check for security measures
        security_found = await self._scan_for_patterns(target, [
            r"encrypt",
            r"hash",
            r"secure",
            r"protect",
            r"confidential"
        ])
        
        principle["requirements"].append({
            "description": "Data security measures",
            "status": "pass" if security_found else "fail",
            "evidence": f"Security patterns found: {len(security_found)}"
        })
        
        passed = sum(1 for req in principle["requirements"] if req["status"] == "pass")
        principle["score"] = passed / len(principle["requirements"])
        
        return principle
    
    async def _check_accountability(self, target: str) -> Dict[str, Any]:
        """Check accountability"""
        principle = {
            "name": "Accountability",
            "requirements": [],
            "score": 0
        }
        
        # Check for audit trails
        accountability_found = await self._scan_for_patterns(target, [
            r"audit",
            r"log",
            r"track",
            r"accountability",
            r"responsible"
        ])
        
        principle["requirements"].append({
            "description": "Accountability measures",
            "status": "pass" if accountability_found else "fail",
            "evidence": f"Accountability patterns found: {len(accountability_found)}"
        })
        
        passed = sum(1 for req in principle["requirements"] if req["status"] == "pass")
        principle["score"] = passed / len(principle["requirements"])
        
        return principle
    
    async def _scan_for_patterns(self, target: str, patterns: List[str]) -> List[str]:
        """Scan for GDPR patterns in code"""
        found = []
        path = Path(target)
        
        for file_path in path.rglob("*.py"):
            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        found.append(f"{file_path}:{pattern}")
            except Exception as e:
                logger.warning("Failed to scan file", file=str(file_path), error=str(e))
        
        return found


class SOC2Checker(ComplianceChecker):
    """SOC 2 Type II compliance checker"""
    
    async def check(self, target: str) -> Dict[str, Any]:
        """Check SOC 2 compliance"""
        results = {
            "standard": "SOC 2 Type II",
            "target": target,
            "timestamp": datetime.utcnow().isoformat(),
            "criteria": [],
            "score": 0
        }
        
        criteria = [
            await self._check_security(target),
            await self._check_availability(target),
            await self._check_processing_integrity(target),
            await self._check_confidentiality(target),
            await self._check_privacy(target)
        ]
        
        results["criteria"] = criteria
        results["score"] = sum(c["score"] for c in criteria) / len(criteria)
        results["status"] = "compliant" if results["score"] >= 0.8 else "non_compliant"
        
        return results
    
    async def _check_security(self, target: str) -> Dict[str, Any]:
        """Check security criteria"""
        criterion = {
            "name": "Security",
            "requirements": [],
            "score": 0
        }
        
        # Check for access controls
        security_found = await self._scan_for_patterns(target, [
            r"authentication",
            r"authorization",
            r"access.*control",
            r"security.*policy",
            r"firewall"
        ])
        
        criterion["requirements"].append({
            "description": "Access controls",
            "status": "pass" if security_found else "fail",
            "evidence": f"Security patterns found: {len(security_found)}"
        })
        
        passed = sum(1 for req in criterion["requirements"] if req["status"] == "pass")
        criterion["score"] = passed / len(criterion["requirements"])
        
        return criterion
    
    async def _check_availability(self, target: str) -> Dict[str, Any]:
        """Check availability criteria"""
        criterion = {
            "name": "Availability",
            "requirements": [],
            "score": 0
        }
        
        # Check for high availability measures
        availability_found = await self._scan_for_patterns(target, [
            r"failover",
            r"redundancy",
            r"backup",
            r"disaster.*recovery",
            r"uptime"
        ])
        
        criterion["requirements"].append({
            "description": "High availability measures",
            "status": "pass" if availability_found else "fail",
            "evidence": f"Availability patterns found: {len(availability_found)}"
        })
        
        passed = sum(1 for req in criterion["requirements"] if req["status"] == "pass")
        criterion["score"] = passed / len(criterion["requirements"])
        
        return criterion
    
    async def _check_processing_integrity(self, target: str) -> Dict[str, Any]:
        """Check processing integrity criteria"""
        criterion = {
            "name": "Processing Integrity",
            "requirements": [],
            "score": 0
        }
        
        # Check for data validation and integrity
        integrity_found = await self._scan_for_patterns(target, [
            r"validation",
            r"integrity",
            r"checksum",
            r"verify",
            r"data.*quality"
        ])
        
        criterion["requirements"].append({
            "description": "Data processing integrity",
            "status": "pass" if integrity_found else "fail",
            "evidence": f"Integrity patterns found: {len(integrity_found)}"
        })
        
        passed = sum(1 for req in criterion["requirements"] if req["status"] == "pass")
        criterion["score"] = passed / len(criterion["requirements"])
        
        return criterion
    
    async def _check_confidentiality(self, target: str) -> Dict[str, Any]:
        """Check confidentiality criteria"""
        criterion = {
            "name": "Confidentiality",
            "requirements": [],
            "score": 0
        }
        
        # Check for encryption and confidentiality measures
        confidentiality_found = await self._scan_for_patterns(target, [
            r"encrypt",
            r"confidential",
            r"secret",
            r"private",
            r"protected"
        ])
        
        criterion["requirements"].append({
            "description": "Confidentiality measures",
            "status": "pass" if confidentiality_found else "fail",
            "evidence": f"Confidentiality patterns found: {len(confidentiality_found)}"
        })
        
        passed = sum(1 for req in criterion["requirements"] if req["status"] == "pass")
        criterion["score"] = passed / len(criterion["requirements"])
        
        return criterion
    
    async def _check_privacy(self, target: str) -> Dict[str, Any]:
        """Check privacy criteria"""
        criterion = {
            "name": "Privacy",
            "requirements": [],
            "score": 0
        }
        
        # Check for privacy controls
        privacy_found = await self._scan_for_patterns(target, [
            r"privacy",
            r"pii",
            r"personal.*data",
            r"anonymize",
            r"consent"
        ])
        
        criterion["requirements"].append({
            "description": "Privacy controls",
            "status": "pass" if privacy_found else "fail",
            "evidence": f"Privacy patterns found: {len(privacy_found)}"
        })
        
        passed = sum(1 for req in criterion["requirements"] if req["status"] == "pass")
        criterion["score"] = passed / len(criterion["requirements"])
        
        return criterion
    
    async def _scan_for_patterns(self, target: str, patterns: List[str]) -> List[str]:
        """Scan for SOC 2 patterns in code"""
        found = []
        path = Path(target)
        
        for file_path in path.rglob("*.py"):
            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        found.append(f"{file_path}:{pattern}")
            except Exception as e:
                logger.warning("Failed to scan file", file=str(file_path), error=str(e))
        
        return found