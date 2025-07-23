"""Email service for beta program notifications"""

import logging
from typing import Optional, Dict, Any
from jinja2 import Template

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service using SendGrid or other providers"""
    
    def __init__(self):
        self.settings = get_settings()
        self._setup_provider()
    
    def _setup_provider(self):
        """Setup email provider based on configuration"""
        if self.settings.email_provider == "sendgrid" and self.settings.email_api_key:
            try:
                import sendgrid
                from sendgrid.helpers.mail import Mail
                self.sg = sendgrid.SendGridAPIClient(api_key=self.settings.email_api_key)
                self.provider = "sendgrid"
            except ImportError:
                logger.warning("SendGrid not available, using mock email")
                self.provider = "mock"
        else:
            self.provider = "mock"
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email"""
        try:
            if self.provider == "sendgrid":
                from sendgrid.helpers.mail import Mail
                
                message = Mail(
                    from_email=(self.settings.email_from_address, self.settings.email_from_name),
                    to_emails=to_email,
                    subject=subject,
                    html_content=html_content,
                    plain_text_content=text_content or html_content
                )
                
                response = self.sg.send(message)
                return response.status_code == 202
            else:
                # Mock email for development
                logger.info(f"Mock email sent to {to_email}: {subject}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


# Email templates
WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f4f4f4; }
        .button { display: inline-block; padding: 10px 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to MAMS Beta Program!</h1>
        </div>
        <div class="content">
            <h2>Hi {{ name }},</h2>
            <p>Thank you for joining the MAMS Beta Program! We're excited to have you on board.</p>
            <p>As a beta tester, you'll get early access to new features and help shape the future of MAMS.</p>
            <h3>What's Next?</h3>
            <ul>
                <li>Explore the new features available to beta users</li>
                <li>Provide feedback on your experience</li>
                <li>Report any bugs you encounter</li>
                <li>Suggest new features or improvements</li>
            </ul>
            <p style="text-align: center;">
                <a href="{{ login_url }}" class="button">Access Beta Features</a>
            </p>
            <p>If you have any questions, feel free to reach out to our support team.</p>
            <p>Best regards,<br>The MAMS Team</p>
        </div>
    </div>
</body>
</html>
"""

INVITATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f4f4f4; }
        .code { background-color: #ecf0f1; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; }
        .button { display: inline-block; padding: 10px 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>You're Invited to MAMS Beta!</h1>
        </div>
        <div class="content">
            <h2>Hi there!</h2>
            <p>{{ inviter_name }} has invited you to join the MAMS Beta Program.</p>
            <p>Your invitation code is:</p>
            <div class="code">{{ invitation_code }}</div>
            <p>Use this code when registering for the beta program to get instant access.</p>
            <p style="text-align: center;">
                <a href="{{ registration_url }}?code={{ invitation_code }}" class="button">Join Beta Program</a>
            </p>
            <p>This invitation is valid for a limited time. Don't miss out on being part of shaping the future of MAMS!</p>
            <p>Best regards,<br>The MAMS Team</p>
        </div>
    </div>
</body>
</html>
"""

FEEDBACK_NOTIFICATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e74c3c; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f4f4f4; }
        .metadata { background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>New Beta Feedback Received</h1>
        </div>
        <div class="content">
            <div class="metadata">
                <strong>Category:</strong> {{ feedback.category }}<br>
                <strong>Title:</strong> {{ feedback.title }}<br>
                <strong>User:</strong> {{ user.full_name }} ({{ user.email }})<br>
                <strong>Severity:</strong> {{ feedback.severity or 'N/A' }}<br>
                <strong>Created:</strong> {{ feedback.created_at }}
            </div>
            <h3>Description:</h3>
            <p>{{ feedback.description }}</p>
            {% if feedback.steps_to_reproduce %}
            <h3>Steps to Reproduce:</h3>
            <p>{{ feedback.steps_to_reproduce }}</p>
            {% endif %}
            <p><a href="{{ admin_url }}/feedback/{{ feedback.id }}">View in Admin Panel</a></p>
        </div>
    </div>
</body>
</html>
"""


# Service instance
email_service = EmailService()


# Helper functions
async def send_beta_welcome_email(email: str, name: str) -> bool:
    """Send welcome email to new beta user"""
    template = Template(WELCOME_TEMPLATE)
    html_content = template.render(
        name=name or "Beta Tester",
        login_url="https://mams.io/beta/login"  # Would be configured
    )
    
    return await email_service.send_email(
        to_email=email,
        subject="Welcome to MAMS Beta Program!",
        html_content=html_content
    )


async def send_beta_invitation_email(
    email: str,
    invitation_code: str,
    inviter_name: str
) -> bool:
    """Send beta invitation email"""
    template = Template(INVITATION_TEMPLATE)
    html_content = template.render(
        inviter_name=inviter_name,
        invitation_code=invitation_code,
        registration_url="https://mams.io/beta/register"  # Would be configured
    )
    
    return await email_service.send_email(
        to_email=email,
        subject=f"{inviter_name} invited you to MAMS Beta!",
        html_content=html_content
    )


async def send_feedback_notification(
    email: str,
    feedback: Any,
    user: Any
) -> bool:
    """Send feedback notification to team"""
    template = Template(FEEDBACK_NOTIFICATION_TEMPLATE)
    html_content = template.render(
        feedback=feedback,
        user=user,
        admin_url="https://admin.mams.io"  # Would be configured
    )
    
    subject = f"[{feedback.category.value}] {feedback.title}"
    if feedback.severity == "critical":
        subject = f"🚨 CRITICAL: {subject}"
    elif feedback.severity == "high":
        subject = f"⚠️ HIGH: {subject}"
    
    return await email_service.send_email(
        to_email=email,
        subject=subject,
        html_content=html_content
    )