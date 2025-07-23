"""Tests for Intrusion Detection Service"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.detection_service import DetectionService
from src.models.db_models import IntrusionEvent, SecurityAlert
from src.core.config import settings


@pytest.fixture
async def detection_service():
    """Create detection service instance"""
    service = DetectionService()
    service.redis = AsyncMock()
    service.threat_intel_cache = {"192.168.1.100", "malicious.com"}
    return service


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = AsyncMock(spec=AsyncSession)
    db.add = Mock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


class TestDetectionService:
    """Test detection service functionality"""
    
    @pytest.mark.asyncio
    async def test_threat_intel_match(self, detection_service, mock_db):
        """Test threat intelligence matching"""
        packet_data = {
            "source_ip": "192.168.1.100",
            "destination_ip": "10.0.0.1",
            "destination_port": 80,
            "protocol": "TCP"
        }
        
        # Mock the alert management
        with patch.object(detection_service, '_manage_alerts', new_callable=AsyncMock):
            event = await detection_service.analyze_network_traffic(mock_db, packet_data)
        
        assert event is not None
        assert event.event_type == "threat_intel_match"
        assert event.severity == "high"
        assert event.source_ip == "192.168.1.100"
        assert "known malicious IP" in event.description
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_port_scan_detection(self, detection_service, mock_db):
        """Test port scan detection"""
        source_ip = "10.0.0.50"
        destination_ip = "10.0.0.1"
        
        # Simulate multiple port access attempts
        detection_service.redis.incr = AsyncMock(side_effect=range(1, 12))
        detection_service.redis.expire = AsyncMock()
        detection_service.detection_rules["port_scan"]["threshold"] = 10
        
        # Mock the alert management
        with patch.object(detection_service, '_manage_alerts', new_callable=AsyncMock):
            event = await detection_service._detect_port_scan(
                mock_db, source_ip, destination_ip
            )
        
        assert event is not None
        assert event.event_type == "port_scan"
        assert event.severity == "high"
        assert event.source_ip == source_ip
        assert event.destination_ip == destination_ip
        assert "Port scan detected" in event.description
    
    @pytest.mark.asyncio
    async def test_ddos_detection(self, detection_service, mock_db):
        """Test DDoS detection"""
        source_ip = "10.0.0.50"
        destination_ip = "10.0.0.1"
        
        # Simulate high request rate
        detection_service.redis.incr = AsyncMock(return_value=1001)
        detection_service.redis.expire = AsyncMock()
        detection_service.detection_rules["ddos"]["threshold"] = 1000
        
        # Mock the alert management
        with patch.object(detection_service, '_manage_alerts', new_callable=AsyncMock):
            event = await detection_service._detect_ddos(
                mock_db, source_ip, destination_ip
            )
        
        assert event is not None
        assert event.event_type == "ddos"
        assert event.severity == "critical"
        assert "Potential DDoS attack" in event.description
    
    @pytest.mark.asyncio
    async def test_suspicious_process_detection(self, detection_service, mock_db):
        """Test suspicious process detection"""
        activity_data = {
            "activity_type": "process_start",
            "user": "testuser",
            "command_line": "nmap -sS 192.168.1.0/24"
        }
        
        # Mock the alert management
        with patch.object(detection_service, '_create_event', new_callable=AsyncMock):
            activity = await detection_service.analyze_system_activity(
                mock_db, activity_data
            )
        
        assert activity is not None
        assert activity.suspicious is True
        assert activity.risk_score == 0.8
        assert activity.command_line == activity_data["command_line"]
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_integrity_check_new_file(self, detection_service, mock_db):
        """Test file integrity check for new file"""
        file_path = "/etc/passwd"
        current_hash = "abc123def456"
        
        # Mock database query for non-existing record
        mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
        
        record = await detection_service.check_file_integrity(
            mock_db, file_path, current_hash
        )
        
        assert record is not None
        assert record.file_path == file_path
        assert record.file_hash == current_hash
        assert record.changed is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_integrity_check_modified_critical_file(self, detection_service, mock_db):
        """Test file integrity check for modified critical file"""
        file_path = "/etc/passwd"
        old_hash = "abc123def456"
        new_hash = "xyz789ghi012"
        
        # Create mock existing record
        existing_record = Mock()
        existing_record.file_path = file_path
        existing_record.file_hash = old_hash
        existing_record.changed = False
        
        mock_db.execute.return_value.scalar_one_or_none = AsyncMock(
            return_value=existing_record
        )
        
        # Mock the alert creation
        with patch.object(detection_service, '_create_event', new_callable=AsyncMock):
            record = await detection_service.check_file_integrity(
                mock_db, file_path, new_hash
            )
        
        assert record is not None
        assert record.changed is True
        assert record.change_type == "modified"
        assert record.previous_hash == old_hash
        assert record.file_hash == new_hash
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, detection_service, mock_db):
        """Test anomaly detection based on baseline"""
        # Set up baseline cache
        detection_service.baseline_cache = {
            "packet_size:10": {"mean": 100, "std": 20}
        }
        
        # Test anomalous packet (z-score > 3)
        packet_data = {
            "size": 200,  # z-score = |200-100|/20 = 5
            "source_ip": "10.0.0.1",
            "destination_ip": "10.0.0.2",
            "destination_port": 80,
            "protocol": "TCP"
        }
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 10
            
            # Mock the alert management
            with patch.object(detection_service, '_create_event', new_callable=AsyncMock) as mock_create:
                result = await detection_service.analyze_network_traffic(
                    mock_db, packet_data
                )
                
                # Check that anomaly event was created
                mock_create.assert_called_once()
                call_args = mock_create.call_args[1]
                assert call_args['event_type'] == 'anomaly'
                assert call_args['severity'] == 'medium'
                assert 'Anomalous network traffic' in call_args['description']
    
    @pytest.mark.asyncio
    async def test_alert_management_new_alert(self, detection_service, mock_db):
        """Test alert management for new alert"""
        event = IntrusionEvent(
            id="event1",
            event_type="port_scan",
            severity="high",
            description="Test port scan",
            timestamp=datetime.utcnow()
        )
        
        # Mock database query for no existing alert
        mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
        
        await detection_service._manage_alerts(mock_db, event)
        
        # Verify new alert was created
        mock_db.add.assert_called_once()
        alert = mock_db.add.call_args[0][0]
        assert isinstance(alert, SecurityAlert)
        assert alert.alert_type == "port_scan"
        assert alert.severity == "high"
        assert alert.event_count == 1
        assert alert.priority == 2  # high severity = priority 2
    
    @pytest.mark.asyncio
    async def test_alert_management_existing_alert(self, detection_service, mock_db):
        """Test alert management for existing alert"""
        # Create existing alert
        existing_alert = SecurityAlert(
            id="alert1",
            alert_type="port_scan",
            severity="medium",
            status="open",
            event_count=5,
            last_seen=datetime.utcnow() - timedelta(minutes=30)
        )
        
        mock_db.execute.return_value.scalar_one_or_none = AsyncMock(
            return_value=existing_alert
        )
        
        # Create new critical event
        event = IntrusionEvent(
            id="event2",
            event_type="port_scan",
            severity="critical",
            description="Critical port scan",
            timestamp=datetime.utcnow()
        )
        
        await detection_service._manage_alerts(mock_db, event)
        
        # Verify alert was updated
        assert existing_alert.event_count == 6
        assert existing_alert.severity == "critical"
        assert existing_alert.priority == 1  # critical severity = priority 1
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_network_baseline(self, detection_service, mock_db):
        """Test network baseline update"""
        metric_name = "packet_size"
        value = 150.0
        
        # Mock no existing baseline
        mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 14
            mock_datetime.now.return_value.weekday.return_value = 2
            
            await detection_service.update_network_baseline(
                mock_db, metric_name, value
            )
        
        # Verify baseline was created
        mock_db.add.assert_called_once()
        baseline = mock_db.add.call_args[0][0]
        assert baseline.metric_name == metric_name
        assert baseline.mean_value == value
        assert baseline.hour_of_day == 14
        assert baseline.day_of_week == 2
        
        # Verify cache was updated
        assert f"{metric_name}:14" in detection_service.baseline_cache