"""
Email Service

Service for sending emails including verification, password reset, and notifications.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
import logging
from jinja2 import Template

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.email_from
        self.from_name = "MAMS"
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email using SMTP"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text part
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            if settings.smtp_use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(message)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        first_name: str,
        verification_token: str
    ) -> bool:
        """Send email verification email"""
        try:
            verification_url = f"http://localhost:3000/verify-email?token={verification_token}"
            
            subject = "Please verify your MAMS account"
            
            html_template = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Verify Your Email</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #2196F3; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background-color: #f9f9f9; }
                    .button { 
                        display: inline-block; 
                        background-color: #2196F3; 
                        color: white; 
                        padding: 12px 24px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }
                    .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to MAMS</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {{ first_name }},</h2>
                        <p>Thank you for signing up for MAMS! Please click the button below to verify your email address:</p>
                        <a href="{{ verification_url }}" class="button">Verify Email Address</a>
                        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                        <p><a href="{{ verification_url }}">{{ verification_url }}</a></p>
                        <p>This link will expire in 24 hours.</p>
                        <p>If you didn't create this account, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 MAMS - Digital Media Asset Management System</p>
                    </div>
                </div>
            </body>
            </html>
            """)
            
            html_content = html_template.render(
                first_name=first_name,
                verification_url=verification_url
            )
            
            text_content = f"""
            Hi {first_name},
            
            Thank you for signing up for MAMS! Please verify your email address by clicking the link below:
            
            {verification_url}
            
            This link will expire in 24 hours.
            
            If you didn't create this account, please ignore this email.
            
            © 2024 MAMS - Digital Media Asset Management System
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            return False
    
    async def send_password_reset_email(
        self,
        to_email: str,
        first_name: str,
        reset_token: str
    ) -> bool:
        """Send password reset email"""
        try:
            reset_url = f"http://localhost:3000/reset-password?token={reset_token}"
            
            subject = "Reset your MAMS password"
            
            html_template = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Reset Your Password</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #FF9800; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background-color: #f9f9f9; }
                    .button { 
                        display: inline-block; 
                        background-color: #FF9800; 
                        color: white; 
                        padding: 12px 24px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }
                    .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                    .warning { background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {{ first_name }},</h2>
                        <p>You requested to reset your MAMS password. Click the button below to create a new password:</p>
                        <a href="{{ reset_url }}" class="button">Reset Password</a>
                        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                        <p><a href="{{ reset_url }}">{{ reset_url }}</a></p>
                        <div class="warning">
                            <strong>Important:</strong> This link will expire in 1 hour for security reasons.
                        </div>
                        <p>If you didn't request this password reset, please ignore this email and your password will remain unchanged.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 MAMS - Digital Media Asset Management System</p>
                    </div>
                </div>
            </body>
            </html>
            """)
            
            html_content = html_template.render(
                first_name=first_name,
                reset_url=reset_url
            )
            
            text_content = f"""
            Hi {first_name},
            
            You requested to reset your MAMS password. Click the link below to create a new password:
            
            {reset_url}
            
            This link will expire in 1 hour for security reasons.
            
            If you didn't request this password reset, please ignore this email and your password will remain unchanged.
            
            © 2024 MAMS - Digital Media Asset Management System
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False
    
    async def send_welcome_email(
        self,
        to_email: str,
        first_name: str,
        organization: Optional[str] = None
    ) -> bool:
        """Send welcome email after email verification"""
        try:
            subject = "Welcome to MAMS!"
            
            html_template = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Welcome to MAMS</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background-color: #f9f9f9; }
                    .button { 
                        display: inline-block; 
                        background-color: #4CAF50; 
                        color: white; 
                        padding: 12px 24px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }
                    .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                    .features { background-color: white; padding: 20px; margin: 20px 0; border-radius: 5px; }
                    .feature { margin: 10px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to MAMS!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {{ first_name }},</h2>
                        <p>Your email has been verified and your MAMS account is now active! {% if organization %}Welcome to {{ organization }}'s media management system.{% endif %}</p>
                        
                        <div class="features">
                            <h3>🚀 Get Started:</h3>
                            <div class="feature">📁 Upload and organize your media assets</div>
                            <div class="feature">🔍 Search and discover content with AI-powered tools</div>
                            <div class="feature">🎬 Create projects and manage editorial workflows</div>
                            <div class="feature">🤝 Collaborate with team members</div>
                            <div class="feature">📊 Track usage and analytics</div>
                        </div>
                        
                        <a href="{{ dashboard_url }}" class="button">Go to Dashboard</a>
                        
                        <p>Need help getting started? Check out our documentation or contact our support team.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 MAMS - Digital Media Asset Management System</p>
                    </div>
                </div>
            </body>
            </html>
            """)
            
            html_content = html_template.render(
                first_name=first_name,
                organization=organization,
                dashboard_url="http://localhost:3000/dashboard"
            )
            
            text_content = f"""
            Hi {first_name},
            
            Your email has been verified and your MAMS account is now active!
            {"Welcome to " + organization + "'s media management system." if organization else ""}
            
            Get Started:
            - Upload and organize your media assets
            - Search and discover content with AI-powered tools
            - Create projects and manage editorial workflows
            - Collaborate with team members
            - Track usage and analytics
            
            Dashboard: http://localhost:3000/dashboard
            
            Need help getting started? Check out our documentation or contact our support team.
            
            © 2024 MAMS - Digital Media Asset Management System
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return False
    
    async def send_account_activation_email(
        self,
        to_email: str,
        first_name: str,
        admin_name: str
    ) -> bool:
        """Send account activation notification"""
        try:
            subject = "Your MAMS account has been activated"
            
            html_template = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Account Activated</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background-color: #f9f9f9; }
                    .button { 
                        display: inline-block; 
                        background-color: #4CAF50; 
                        color: white; 
                        padding: 12px 24px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }
                    .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Account Activated</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {{ first_name }},</h2>
                        <p>Good news! Your MAMS account has been activated by {{ admin_name }}.</p>
                        <p>You can now access all the features of your media management system.</p>
                        <a href="{{ login_url }}" class="button">Login to MAMS</a>
                    </div>
                    <div class="footer">
                        <p>© 2024 MAMS - Digital Media Asset Management System</p>
                    </div>
                </div>
            </body>
            </html>
            """)
            
            html_content = html_template.render(
                first_name=first_name,
                admin_name=admin_name,
                login_url="http://localhost:3000/login"
            )
            
            text_content = f"""
            Hi {first_name},
            
            Good news! Your MAMS account has been activated by {admin_name}.
            
            You can now access all the features of your media management system.
            
            Login: http://localhost:3000/login
            
            © 2024 MAMS - Digital Media Asset Management System
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send activation email: {e}")
            return False