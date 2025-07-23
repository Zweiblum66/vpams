"""
Notification utilities for failover events
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import structlog

from ..core.config import settings
from ..models.schemas import FailoverEvent, NotificationConfig

logger = structlog.get_logger(__name__)


class NotificationManager:
    """
    Manages notifications for failover events
    """
    
    def __init__(self):
        self.config = NotificationConfig(
            enabled=settings.ENABLE_NOTIFICATIONS,
            channels=["webhook", "email", "slack"],
            recipients={
                "email": settings.NOTIFICATION_EMAILS,
                "webhook": settings.NOTIFICATION_WEBHOOKS,
                "slack": [settings.SLACK_WEBHOOK_URL] if settings.SLACK_WEBHOOK_URL else []
            }
        )
        self.http_client = httpx.AsyncClient()
        self._notification_history: List[Dict[str, Any]] = []
        self._rate_limit_counter: Dict[str, int] = {}
    
    async def send_failover_notification(self, message: str, event: FailoverEvent):
        """Send failover event notification"""
        if not self.config.enabled:
            return
        
        notification = {
            "type": "failover",
            "severity": "critical",
            "message": message,
            "event": event.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._send_to_all_channels(notification)
    
    async def send_critical_alert(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Send critical alert"""
        if not self.config.enabled:
            return
        
        notification = {
            "type": "alert",
            "severity": "critical",
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._send_to_all_channels(notification)
    
    async def send_warning(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Send warning notification"""
        if not self.config.enabled:
            return
        
        notification = {
            "type": "warning",
            "severity": "warning",
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._send_to_all_channels(notification)
    
    async def send_info(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Send informational notification"""
        if not self.config.enabled:
            return
        
        notification = {
            "type": "info",
            "severity": "info",
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._send_to_all_channels(notification)
    
    async def _send_to_all_channels(self, notification: Dict[str, Any]):
        """Send notification to all configured channels"""
        # Check rate limiting
        if not self._check_rate_limit(notification["severity"]):
            logger.warning("Notification rate limit exceeded")
            return
        
        tasks = []
        
        # Send to webhooks
        for webhook_url in self.config.recipients.get("webhook", []):
            task = self._send_webhook(webhook_url, notification)
            tasks.append(task)
        
        # Send to Slack
        for slack_url in self.config.recipients.get("slack", []):
            task = self._send_slack(slack_url, notification)
            tasks.append(task)
        
        # Send emails (would implement actual email sending)
        for email in self.config.recipients.get("email", []):
            task = self._send_email(email, notification)
            tasks.append(task)
        
        # Send to PagerDuty if configured
        if settings.PAGERDUTY_INTEGRATION_KEY and notification["severity"] == "critical":
            task = self._send_pagerduty(notification)
            tasks.append(task)
        
        # Execute all notifications in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Notification failed: {result}")
        
        # Store in history
        self._notification_history.append(notification)
        if len(self._notification_history) > 1000:
            self._notification_history = self._notification_history[-1000:]
    
    async def _send_webhook(self, url: str, notification: Dict[str, Any]):
        """Send webhook notification"""
        try:
            response = await self.http_client.post(
                url,
                json=notification,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Webhook notification sent to {url}")
        except Exception as e:
            logger.error(f"Failed to send webhook to {url}: {e}")
            raise
    
    async def _send_slack(self, webhook_url: str, notification: Dict[str, Any]):
        """Send Slack notification"""
        # Format message for Slack
        color = {
            "critical": "danger",
            "warning": "warning",
            "info": "good"
        }.get(notification["severity"], "warning")
        
        slack_message = {
            "attachments": [{
                "color": color,
                "title": f"{notification['type'].upper()}: {notification['message']}",
                "text": json.dumps(notification.get("details", {}), indent=2),
                "footer": "MAMS Failover Service",
                "ts": int(datetime.utcnow().timestamp())
            }]
        }
        
        try:
            response = await self.http_client.post(
                webhook_url,
                json=slack_message,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info("Slack notification sent")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            raise
    
    async def _send_email(self, email: str, notification: Dict[str, Any]):
        """Send email notification"""
        # In production, would use actual email service (SendGrid, SES, etc.)
        logger.info(f"Would send email to {email}: {notification['message']}")
        await asyncio.sleep(0.1)  # Simulate email sending
    
    async def _send_pagerduty(self, notification: Dict[str, Any]):
        """Send PagerDuty alert"""
        pagerduty_event = {
            "routing_key": settings.PAGERDUTY_INTEGRATION_KEY,
            "event_action": "trigger",
            "payload": {
                "summary": notification["message"],
                "severity": "critical",
                "source": "mams-failover",
                "custom_details": notification.get("details", {})
            }
        }
        
        try:
            response = await self.http_client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=pagerduty_event,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info("PagerDuty alert sent")
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            raise
    
    def _check_rate_limit(self, severity: str) -> bool:
        """Check if notification is within rate limits"""
        current_hour = datetime.utcnow().strftime("%Y%m%d%H")
        key = f"{severity}:{current_hour}"
        
        count = self._rate_limit_counter.get(key, 0)
        if count >= self.config.rate_limit_per_hour:
            return False
        
        self._rate_limit_counter[key] = count + 1
        
        # Clean old entries
        if len(self._rate_limit_counter) > 100:
            self._rate_limit_counter.clear()
        
        return True
    
    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        return self._notification_history[-limit:]
    
    async def test_notifications(self) -> Dict[str, bool]:
        """Test all notification channels"""
        test_notification = {
            "type": "test",
            "severity": "info",
            "message": "Test notification from MAMS Failover Service",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        results = {}
        
        # Test each channel
        for channel, recipients in self.config.recipients.items():
            if not recipients:
                results[channel] = False
                continue
            
            try:
                if channel == "webhook":
                    await self._send_webhook(recipients[0], test_notification)
                elif channel == "slack":
                    await self._send_slack(recipients[0], test_notification)
                elif channel == "email":
                    await self._send_email(recipients[0], test_notification)
                
                results[channel] = True
            except Exception as e:
                logger.error(f"Test failed for {channel}: {e}")
                results[channel] = False
        
        return results
    
    async def close(self):
        """Close notification manager"""
        await self.http_client.aclose()