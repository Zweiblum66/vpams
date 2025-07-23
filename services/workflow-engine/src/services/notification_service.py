"""
Notification service for sending approval notifications
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

from ..core.config import settings
from ..core.exceptions import WorkflowException
from ..models.approval_schemas import NotificationPriority

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    SLACK = "slack"
    TEAMS = "teams"


class NotificationTemplate(Enum):
    """Predefined notification templates"""
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_REMINDER = "approval_reminder"
    APPROVAL_ESCALATION = "approval_escalation"
    APPROVAL_COMPLETED = "approval_completed"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_CANCELLED = "approval_cancelled"
    SLA_WARNING = "sla_warning"
    STATUS_UPDATE = "status_update"


class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self):
        self.templates = self._load_templates()
        self.channel_handlers = {
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.IN_APP: self._send_in_app,
            NotificationChannel.SLACK: self._send_slack,
            NotificationChannel.TEAMS: self._send_teams,
        }
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load notification templates"""
        return {
            NotificationTemplate.APPROVAL_REQUEST.value: {
                "subject": "New Approval Request: {title}",
                "body": """
                You have a new approval request that requires your attention.
                
                Title: {title}
                Description: {description}
                Requested by: {requestor}
                Priority: {priority}
                Deadline: {deadline}
                
                Please review and take action at your earliest convenience.
                """
            },
            NotificationTemplate.APPROVAL_REMINDER.value: {
                "subject": "Reminder: Approval Request Pending - {title}",
                "body": """
                This is a reminder that you have a pending approval request.
                
                Title: {title}
                Time pending: {time_pending}
                Deadline: {deadline}
                
                Please take action to avoid escalation.
                """
            },
            NotificationTemplate.APPROVAL_ESCALATION.value: {
                "subject": "URGENT: Approval Escalated - {title}",
                "body": """
                An approval request has been escalated to you.
                
                Title: {title}
                Escalation reason: {reason}
                Original approver: {original_approver}
                Time overdue: {time_overdue}
                
                Immediate action required.
                """
            },
            NotificationTemplate.APPROVAL_COMPLETED.value: {
                "subject": "Approval Completed: {title}",
                "body": """
                Your approval request has been completed.
                
                Title: {title}
                Status: {status}
                Completed by: {approver}
                Comments: {comments}
                
                Thank you for using the approval system.
                """
            },
            NotificationTemplate.SLA_WARNING.value: {
                "subject": "SLA Warning: Approval Approaching Deadline - {title}",
                "body": """
                An approval request is approaching its SLA deadline.
                
                Title: {title}
                Time remaining: {time_remaining}
                Assigned to: {assignee}
                
                Please ensure timely completion.
                """
            }
        }
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        template: Optional[NotificationTemplate] = None,
        template_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send notification to user
        
        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification message
            priority: Notification priority
            channels: Delivery channels (defaults to user preferences)
            metadata: Additional metadata
            template: Use predefined template
            template_data: Data for template substitution
            
        Returns:
            Notification result
        """
        try:
            # Use template if provided
            if template and template.value in self.templates:
                template_config = self.templates[template.value]
                if template_data:
                    title = template_config["subject"].format(**template_data)
                    message = template_config["body"].format(**template_data)
            
            # Get user notification preferences
            if not channels:
                channels = await self._get_user_channels(user_id, priority)
            
            # Send to each channel
            results = {}
            for channel in channels:
                if channel in self.channel_handlers:
                    try:
                        result = await self.channel_handlers[channel](
                            user_id, title, message, priority, metadata
                        )
                        results[channel.value] = result
                    except Exception as e:
                        logger.error(f"Failed to send {channel.value} notification: {e}")
                        results[channel.value] = {"success": False, "error": str(e)}
            
            # Log notification
            logger.info(
                f"Sent notification to {user_id}: {title} "
                f"via {[c.value for c in channels]}"
            )
            
            return {
                "success": True,
                "channels": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise WorkflowException(f"Failed to send notification: {e}")
    
    async def send_bulk_notifications(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template: Optional[NotificationTemplate] = None,
        template_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send notification to multiple users"""
        tasks = []
        for user_id in user_ids:
            task = self.send_notification(
                user_id=user_id,
                title=title,
                message=message,
                priority=priority,
                template=template,
                template_data=template_data
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        
        return {
            "total": len(user_ids),
            "successful": successful,
            "failed": failed,
            "results": results
        }
    
    async def _get_user_channels(
        self,
        user_id: str,
        priority: NotificationPriority
    ) -> List[NotificationChannel]:
        """Get user's preferred notification channels"""
        # In production, this would fetch from user preferences
        # For now, return defaults based on priority
        if priority == NotificationPriority.CRITICAL:
            return [
                NotificationChannel.EMAIL,
                NotificationChannel.IN_APP,
                NotificationChannel.SLACK
            ]
        elif priority == NotificationPriority.HIGH:
            return [NotificationChannel.EMAIL, NotificationChannel.IN_APP]
        else:
            return [NotificationChannel.IN_APP]
    
    async def _send_email(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send email notification"""
        try:
            # In production, integrate with email service
            # For now, just log
            logger.info(f"Email notification to {user_id}: {title}")
            
            # Simulate email sending
            email_data = {
                "to": f"{user_id}@example.com",
                "subject": title,
                "body": message,
                "priority": priority.value,
                "metadata": metadata
            }
            
            # Here you would integrate with SMTP or email service API
            # For example: await send_email_via_smtp(email_data)
            
            return {"success": True, "message_id": f"email_{datetime.utcnow().timestamp()}"}
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_in_app(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send in-app notification"""
        try:
            # In production, this would create a notification in the database
            # and potentially push via WebSocket
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "priority": priority.value,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
                "read": False
            }
            
            # Here you would save to database and push via WebSocket
            # For example: await save_notification(notification_data)
            #              await push_via_websocket(user_id, notification_data)
            
            logger.info(f"In-app notification created for {user_id}: {title}")
            
            return {"success": True, "notification_id": f"notif_{datetime.utcnow().timestamp()}"}
            
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_slack(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send Slack notification"""
        try:
            # In production, integrate with Slack API
            slack_message = {
                "channel": f"@{user_id}",
                "text": title,
                "attachments": [{
                    "color": self._get_slack_color(priority),
                    "text": message,
                    "fields": [
                        {"title": k, "value": str(v), "short": True}
                        for k, v in (metadata or {}).items()
                    ]
                }]
            }
            
            # Here you would send via Slack API
            # For example: await slack_client.post_message(slack_message)
            
            logger.info(f"Slack notification to {user_id}: {title}")
            
            return {"success": True, "ts": datetime.utcnow().timestamp()}
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_teams(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send Microsoft Teams notification"""
        try:
            # In production, integrate with Teams API
            teams_card = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": self._get_teams_color(priority),
                "sections": [{
                    "activityTitle": title,
                    "text": message,
                    "facts": [
                        {"name": k, "value": str(v)}
                        for k, v in (metadata or {}).items()
                    ]
                }]
            }
            
            # Here you would send via Teams webhook
            # For example: await teams_webhook.post(teams_card)
            
            logger.info(f"Teams notification to {user_id}: {title}")
            
            return {"success": True, "message_id": f"teams_{datetime.utcnow().timestamp()}"}
            
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_slack_color(self, priority: NotificationPriority) -> str:
        """Get Slack attachment color based on priority"""
        colors = {
            NotificationPriority.LOW: "#36a64f",      # Green
            NotificationPriority.NORMAL: "#3aa3e3",   # Blue
            NotificationPriority.HIGH: "#ff9900",     # Orange
            NotificationPriority.CRITICAL: "#ff0000"  # Red
        }
        return colors.get(priority, "#808080")  # Gray default
    
    def _get_teams_color(self, priority: NotificationPriority) -> str:
        """Get Teams card color based on priority"""
        colors = {
            NotificationPriority.LOW: "00FF00",      # Green
            NotificationPriority.NORMAL: "0078D4",   # Blue
            NotificationPriority.HIGH: "FF8C00",     # Orange
            NotificationPriority.CRITICAL: "FF0000"  # Red
        }
        return colors.get(priority, "808080")  # Gray default
    
    async def get_notification_stats(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification statistics"""
        # In production, this would query notification history
        return {
            "total_sent": 0,
            "by_channel": {
                "email": 0,
                "in_app": 0,
                "slack": 0,
                "teams": 0
            },
            "by_priority": {
                "low": 0,
                "normal": 0,
                "high": 0,
                "critical": 0
            },
            "failed": 0
        }