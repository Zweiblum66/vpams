"""Intrusion Detection Service - Core detection logic"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog
import aioredis
import psutil
import socket

from src.models.db_models import (
    IntrusionEvent, SecurityAlert, NetworkBaseline,
    ThreatIntelligence, FileIntegrityRecord, SystemActivity
)
from src.core.config import settings

logger = structlog.get_logger()


class DetectionService:
    """Main intrusion detection service"""
    
    def __init__(self):
        self.redis = None
        self.detection_rules = {}
        self.baseline_cache = {}
        self.threat_intel_cache = set()
        
    async def initialize(self):
        """Initialize the detection service"""
        # Connect to Redis
        self.redis = await aioredis.from_url(settings.redis_url)
        
        # Load detection rules
        await self._load_detection_rules()
        
        # Load threat intelligence
        await self._load_threat_intelligence()
        
        logger.info("Intrusion detection service initialized")
    
    async def _load_detection_rules(self):
        """Load detection rules from configuration"""
        # Default detection rules
        self.detection_rules = {
            "port_scan": {
                "threshold": settings.port_scan_threshold,
                "time_window": 60,  # seconds
                "severity": "high"
            },
            "brute_force": {
                "threshold": settings.max_failed_logins,
                "time_window": 300,  # seconds
                "severity": "high"
            },
            "ddos": {
                "threshold": settings.ddos_threshold,
                "time_window": 10,  # seconds
                "severity": "critical"
            },
            "suspicious_process": {
                "patterns": [
                    "nc -l", "nmap", "nikto", "sqlmap",
                    "metasploit", "mimikatz", "powershell -enc"
                ],
                "severity": "high"
            },
            "file_modification": {
                "critical_paths": [
                    "/etc/passwd", "/etc/shadow", "/etc/sudoers",
                    "/etc/ssh/sshd_config", "/etc/hosts"
                ],
                "severity": "critical"
            }
        }
    
    async def _load_threat_intelligence(self):
        """Load threat intelligence indicators"""
        # This would load from database/external feeds
        # For now, using a simple set
        self.threat_intel_cache = {
            "192.168.1.100",  # Example malicious IPs
            "10.0.0.50",
            "evil.com",
            "malware.org"
        }
    
    async def analyze_network_traffic(
        self,
        db: AsyncSession,
        packet_data: Dict[str, Any]
    ) -> Optional[IntrusionEvent]:
        """Analyze network traffic for intrusions"""
        source_ip = packet_data.get("source_ip")
        destination_ip = packet_data.get("destination_ip")
        destination_port = packet_data.get("destination_port")
        protocol = packet_data.get("protocol")
        
        # Check against threat intelligence
        if source_ip in self.threat_intel_cache:
            return await self._create_event(
                db,
                event_type="threat_intel_match",
                severity="high",
                source_ip=source_ip,
                destination_ip=destination_ip,
                destination_port=destination_port,
                protocol=protocol,
                description=f"Connection from known malicious IP: {source_ip}",
                detection_method="threat_intelligence"
            )
        
        # Check for port scanning
        port_scan_event = await self._detect_port_scan(
            db, source_ip, destination_ip
        )
        if port_scan_event:
            return port_scan_event
        
        # Check for DDoS patterns
        ddos_event = await self._detect_ddos(
            db, source_ip, destination_ip
        )
        if ddos_event:
            return ddos_event
        
        # Anomaly detection
        if await self._is_anomalous_traffic(packet_data):
            return await self._create_event(
                db,
                event_type="anomaly",
                severity="medium",
                source_ip=source_ip,
                destination_ip=destination_ip,
                destination_port=destination_port,
                protocol=protocol,
                description="Anomalous network traffic detected",
                detection_method="anomaly"
            )
        
        return None
    
    async def _detect_port_scan(
        self,
        db: AsyncSession,
        source_ip: str,
        destination_ip: str
    ) -> Optional[IntrusionEvent]:
        """Detect port scanning activity"""
        # Check recent connection attempts from this IP
        key = f"port_scan:{source_ip}:{destination_ip}"
        
        # Increment counter in Redis
        count = await self.redis.incr(key)
        if count == 1:
            # Set expiry for the time window
            await self.redis.expire(key, self.detection_rules["port_scan"]["time_window"])
        
        # Check if threshold exceeded
        if count >= self.detection_rules["port_scan"]["threshold"]:
            return await self._create_event(
                db,
                event_type="port_scan",
                severity=self.detection_rules["port_scan"]["severity"],
                source_ip=source_ip,
                destination_ip=destination_ip,
                description=f"Port scan detected from {source_ip} to {destination_ip}",
                detection_method="signature"
            )
        
        return None
    
    async def _detect_ddos(
        self,
        db: AsyncSession,
        source_ip: str,
        destination_ip: str
    ) -> Optional[IntrusionEvent]:
        """Detect DDoS attacks"""
        # Track request rate
        key = f"ddos:{destination_ip}"
        
        # Increment counter
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, self.detection_rules["ddos"]["time_window"])
        
        # Check if threshold exceeded
        if count >= self.detection_rules["ddos"]["threshold"]:
            return await self._create_event(
                db,
                event_type="ddos",
                severity=self.detection_rules["ddos"]["severity"],
                source_ip=source_ip,
                destination_ip=destination_ip,
                description=f"Potential DDoS attack on {destination_ip}",
                detection_method="behavioral"
            )
        
        return None
    
    async def _is_anomalous_traffic(
        self,
        packet_data: Dict[str, Any]
    ) -> bool:
        """Check if traffic is anomalous based on baselines"""
        # Get current hour for baseline comparison
        current_hour = datetime.now().hour
        
        # Extract features from packet
        packet_size = packet_data.get("size", 0)
        
        # Get baseline for this metric
        baseline_key = f"packet_size:{current_hour}"
        baseline = self.baseline_cache.get(baseline_key)
        
        if baseline:
            # Calculate z-score
            z_score = abs((packet_size - baseline["mean"]) / baseline["std"])
            
            # Flag as anomalous if z-score > 3
            return z_score > 3
        
        return False
    
    async def analyze_system_activity(
        self,
        db: AsyncSession,
        activity_data: Dict[str, Any]
    ) -> Optional[SystemActivity]:
        """Analyze system activity for suspicious behavior"""
        activity_type = activity_data.get("activity_type")
        user = activity_data.get("user")
        command_line = activity_data.get("command_line", "")
        
        # Check for suspicious processes
        suspicious = False
        risk_score = 0.0
        
        if activity_type == "process_start" and command_line:
            for pattern in self.detection_rules["suspicious_process"]["patterns"]:
                if pattern.lower() in command_line.lower():
                    suspicious = True
                    risk_score = 0.8
                    
                    # Create intrusion event
                    await self._create_event(
                        db,
                        event_type="suspicious_process",
                        severity=self.detection_rules["suspicious_process"]["severity"],
                        description=f"Suspicious process detected: {command_line}",
                        detection_method="signature",
                        raw_data=activity_data
                    )
                    break
        
        # Log system activity
        activity = SystemActivity(
            timestamp=datetime.utcnow(),
            activity_type=activity_type,
            user=user,
            command_line=command_line,
            suspicious=suspicious,
            risk_score=risk_score,
            metadata=activity_data
        )
        
        db.add(activity)
        await db.commit()
        
        return activity
    
    async def check_file_integrity(
        self,
        db: AsyncSession,
        file_path: str,
        current_hash: str
    ) -> Optional[FileIntegrityRecord]:
        """Check file integrity for unauthorized changes"""
        # Get existing record
        result = await db.execute(
            select(FileIntegrityRecord).where(
                FileIntegrityRecord.file_path == file_path
            )
        )
        record = result.scalar_one_or_none()
        
        if record:
            # Check if file has changed
            if record.file_hash != current_hash:
                record.changed = True
                record.change_type = "modified"
                record.previous_hash = record.file_hash
                record.file_hash = current_hash
                record.last_modified = datetime.utcnow()
                
                # Check if it's a critical file
                for critical_path in self.detection_rules["file_modification"]["critical_paths"]:
                    if file_path.startswith(critical_path):
                        await self._create_event(
                            db,
                            event_type="file_modification",
                            severity=self.detection_rules["file_modification"]["severity"],
                            description=f"Critical file modified: {file_path}",
                            detection_method="file_integrity",
                            raw_data={"file_path": file_path, "old_hash": record.previous_hash, "new_hash": current_hash}
                        )
                        break
        else:
            # Create new record
            record = FileIntegrityRecord(
                file_path=file_path,
                file_hash=current_hash,
                last_checked=datetime.utcnow()
            )
            db.add(record)
        
        record.last_checked = datetime.utcnow()
        await db.commit()
        
        return record
    
    async def _create_event(
        self,
        db: AsyncSession,
        event_type: str,
        severity: str,
        description: str,
        detection_method: str,
        **kwargs
    ) -> IntrusionEvent:
        """Create an intrusion event"""
        event = IntrusionEvent(
            event_type=event_type,
            severity=severity,
            description=description,
            detection_method=detection_method,
            timestamp=datetime.utcnow(),
            **kwargs
        )
        
        db.add(event)
        await db.commit()
        
        # Check if we need to create or update an alert
        await self._manage_alerts(db, event)
        
        # Log the event
        logger.warning(
            "Intrusion detected",
            event_type=event_type,
            severity=severity,
            description=description
        )
        
        return event
    
    async def _manage_alerts(
        self,
        db: AsyncSession,
        event: IntrusionEvent
    ):
        """Manage security alerts based on events"""
        # Check for existing open alert of this type
        result = await db.execute(
            select(SecurityAlert).where(
                and_(
                    SecurityAlert.alert_type == event.event_type,
                    SecurityAlert.status == "open",
                    SecurityAlert.last_seen >= datetime.utcnow() - timedelta(hours=1)
                )
            )
        )
        alert = result.scalar_one_or_none()
        
        if alert:
            # Update existing alert
            alert.last_seen = datetime.utcnow()
            alert.event_count += 1
            
            # Escalate severity if needed
            if event.severity == "critical" and alert.severity != "critical":
                alert.severity = "critical"
                alert.priority = 1
        else:
            # Create new alert
            alert = SecurityAlert(
                title=f"{event.event_type.replace('_', ' ').title()} Detected",
                description=event.description,
                severity=event.severity,
                alert_type=event.event_type,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                event_count=1,
                priority=self._get_priority_from_severity(event.severity)
            )
            db.add(alert)
        
        # Link event to alert
        event.alert = alert
        await db.commit()
    
    def _get_priority_from_severity(self, severity: str) -> int:
        """Convert severity to priority (1-5)"""
        mapping = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }
        return mapping.get(severity, 3)
    
    async def update_network_baseline(
        self,
        db: AsyncSession,
        metric_name: str,
        value: float
    ):
        """Update network baseline for anomaly detection"""
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        # Get or create baseline record
        result = await db.execute(
            select(NetworkBaseline).where(
                and_(
                    NetworkBaseline.metric_name == metric_name,
                    NetworkBaseline.hour_of_day == current_hour,
                    NetworkBaseline.day_of_week == current_day
                )
            )
        )
        baseline = result.scalar_one_or_none()
        
        if baseline:
            # Update baseline with exponential moving average
            alpha = 0.1  # Learning rate
            baseline.mean_value = (1 - alpha) * baseline.mean_value + alpha * value
            baseline.sample_count += 1
            baseline.last_updated = datetime.utcnow()
        else:
            # Create new baseline
            baseline = NetworkBaseline(
                metric_name=metric_name,
                hour_of_day=current_hour,
                day_of_week=current_day,
                mean_value=value,
                std_deviation=0,
                min_value=value,
                max_value=value,
                percentile_95=value,
                sample_count=1,
                last_updated=datetime.utcnow()
            )
            db.add(baseline)
        
        await db.commit()
        
        # Update cache
        cache_key = f"{metric_name}:{current_hour}"
        self.baseline_cache[cache_key] = {
            "mean": baseline.mean_value,
            "std": max(baseline.std_deviation, 1.0)  # Avoid division by zero
        }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics for monitoring"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Get active connections
        connections = psutil.net_connections()
        active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "active_connections": active_connections,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis:
            await self.redis.close()
        logger.info("Intrusion detection service cleaned up")