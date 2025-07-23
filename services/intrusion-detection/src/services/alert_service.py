"""Alert Service for sending notifications about security incidents"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import structlog
from slack_sdk.webhook.async_client import AsyncWebhookClient
from jinja2 import Template

from src.models.db_models import SecurityAlert, IntrusionEvent
from src.core.config import settings

logger = structlog.get_logger()


class AlertService:
    """Service for sending security alerts through various channels"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.slack_client = None
        if settings.slack_webhook_url:
            self.slack_client = AsyncWebhookClient(settings.slack_webhook_url)
        
        # Alert templates
        self.email_template = """
        <html>
        <body>
            <h2>Security Alert: {{ alert.title }}</h2>
            <p><strong>Severity:</strong> <span style="color: {{ severity_color }}">{{ alert.severity | upper }}</span></p>
            <p><strong>Time:</strong> {{ alert.created_at }}</p>
            <p><strong>Description:</strong> {{ alert.description }}</p>
            
            <h3>Details:</h3>
            <ul>
                <li><strong>Alert Type:</strong> {{ alert.alert_type }}</li>
                <li><strong>Event Count:</strong> {{ alert.event_count }}</li>
                <li><strong>First Seen:</strong> {{ alert.first_seen }}</li>
                <li><strong>Last Seen:</strong> {{ alert.last_seen }}</li>
            </ul>
            
            {% if events %}
            <h3>Recent Events:</h3>
            <table border="1" cellpadding="5">
                <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Source IP</th>
                    <th>Description</th>
                </tr>
                {% for event in events %}
                <tr>
                    <td>{{ event.timestamp }}</td>
                    <td>{{ event.event_type }}</td>
                    <td>{{ event.source_ip or 'N/A' }}</td>
                    <td>{{ event.description }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}
            
            {% if recommendations %}
            <h3>Recommendations:</h3>
            <ul>
                {% for rec in recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            
            <p><small>This is an automated alert from MAMS Intrusion Detection System</small></p>
        </body>
        </html>
        """
    
    async def send_alert(
        self,
        alert: SecurityAlert,
        events: List[IntrusionEvent],
        force: bool = False
    ):
        """Send alert through configured channels"""
        # Check if alert should be sent
        if not force and not self._should_send_alert(alert):
            return
        
        # Prepare alert data
        alert_data = self._prepare_alert_data(alert, events)
        
        # Send through various channels
        tasks = []
        
        if settings.alert_webhook_url:
            tasks.append(self._send_webhook_alert(alert_data))
        
        if settings.slack_webhook_url:
            tasks.append(self._send_slack_alert(alert_data))
        
        if settings.alert_email_enabled and settings.alert_email_to:
            tasks.append(self._send_email_alert(alert_data))
        
        # Execute all tasks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to send alert via channel {i}", error=str(result))
    
    def _should_send_alert(self, alert: SecurityAlert) -> bool:
        """Determine if alert should be sent based on severity and frequency"""
        # Always send critical alerts
        if alert.severity == "critical":
            return True
        
        # Send high severity alerts with event count threshold
        if alert.severity == "high" and alert.event_count >= 3:
            return True
        
        # Send medium severity alerts with higher threshold
        if alert.severity == "medium" and alert.event_count >= 10:
            return True
        
        return False
    
    def _prepare_alert_data(
        self,
        alert: SecurityAlert,
        events: List[IntrusionEvent]
    ) -> Dict[str, Any]:
        """Prepare alert data for sending"""
        # Get severity color
        severity_colors = {
            "critical": "#FF0000",
            "high": "#FF6600",
            "medium": "#FFCC00",
            "low": "#00CC00"
        }
        
        # Generate recommendations based on alert type
        recommendations = self._get_recommendations(alert)
        
        return {
            "alert": alert,
            "events": events[:10],  # Limit to recent 10 events
            "severity_color": severity_colors.get(alert.severity, "#666666"),
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_recommendations(self, alert: SecurityAlert) -> List[str]:
        """Get recommendations based on alert type"""
        recommendations_map = {
            "port_scan": [
                "Review firewall rules for unnecessary open ports",
                "Investigate the source IP for malicious activity",
                "Consider implementing rate limiting",
                "Enable port scan detection in firewall"
            ],
            "brute_force": [
                "Implement account lockout policies",
                "Enable two-factor authentication",
                "Review password complexity requirements",
                "Consider implementing CAPTCHA for login forms"
            ],
            "ddos": [
                "Enable DDoS protection at network edge",
                "Implement rate limiting",
                "Consider using a CDN with DDoS protection",
                "Review server capacity and scaling options"
            ],
            "suspicious_process": [
                "Investigate the process and its origin",
                "Review system for signs of compromise",
                "Update antivirus/antimalware signatures",
                "Consider implementing application whitelisting"
            ],
            "file_modification": [
                "Verify the file modification was authorized",
                "Check system logs for unauthorized access",
                "Review user permissions and access controls",
                "Consider implementing file integrity monitoring"
            ],
            "threat_intel_match": [
                "Block the malicious IP at firewall level",
                "Investigate any connections to/from the IP",
                "Update threat intelligence feeds",
                "Review logs for additional indicators of compromise"
            ]
        }
        
        return recommendations_map.get(alert.alert_type, [
            "Investigate the alert details",
            "Review system logs for related activity",
            "Consider updating security policies"
        ])
    
    async def _send_webhook_alert(self, alert_data: Dict[str, Any]):
        """Send alert via webhook"""
        try:
            # Prepare webhook payload
            payload = {
                "alert_id": str(alert_data["alert"].id),
                "title": alert_data["alert"].title,
                "severity": alert_data["alert"].severity,
                "description": alert_data["alert"].description,
                "alert_type": alert_data["alert"].alert_type,
                "event_count": alert_data["alert"].event_count,
                "first_seen": alert_data["alert"].first_seen.isoformat(),
                "last_seen": alert_data["alert"].last_seen.isoformat(),
                "recommendations": alert_data["recommendations"],
                "timestamp": alert_data["timestamp"]
            }
            
            response = await self.http_client.post(
                settings.alert_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            logger.info(
                "Webhook alert sent",
                alert_id=str(alert_data["alert"].id),
                status_code=response.status_code
            )
            
        except Exception as e:
            logger.error("Failed to send webhook alert", error=str(e))
            raise
    
    async def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send alert to Slack"""
        try:
            alert = alert_data["alert"]
            
            # Prepare Slack message with blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 Security Alert: {alert.title}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:* {self._get_severity_emoji(alert.severity)} {alert.severity.upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Alert Type:* {alert.alert_type}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Event Count:* {alert.event_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:* {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:* {alert.description}"
                    }
                }
            ]
            
            # Add recommendations if any
            if alert_data["recommendations"]:
                rec_text = "\n".join([f"• {rec}" for rec in alert_data["recommendations"]])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommended Actions:*\n{rec_text}"
                    }
                })
            
            # Send to Slack
            response = await self.slack_client.send(
                text=f"Security Alert: {alert.title}",
                blocks=blocks
            )
            
            logger.info(
                "Slack alert sent",
                alert_id=str(alert.id),
                status_code=response.status_code
            )
            
        except Exception as e:
            logger.error("Failed to send Slack alert", error=str(e))
            raise
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level"""
        emojis = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }
        return emojis.get(severity, "⚪")
    
    async def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Send alert via email"""
        try:
            alert = alert_data["alert"]
            
            # Render email template
            template = Template(self.email_template)
            html_content = template.render(**alert_data)
            
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.upper()}] Security Alert: {alert.title}"
            msg["From"] = settings.alert_email_from
            msg["To"] = ", ".join(settings.alert_email_to)
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=settings.alert_email_smtp_host,
                port=settings.alert_email_smtp_port,
                start_tls=True
            )
            
            logger.info(
                "Email alert sent",
                alert_id=str(alert.id),
                recipients=settings.alert_email_to
            )
            
        except Exception as e:
            logger.error("Failed to send email alert", error=str(e))
            raise
    
    async def send_daily_summary(self, summary_data: Dict[str, Any]):
        """Send daily security summary"""
        # This could be implemented to send a daily digest of security events
        pass
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()