"""
Test cases for Email Service

This module tests the email sending functionality including
verification emails, password reset emails, and notifications.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from services.email_service import EmailService
from core.config import get_settings


class TestEmailService:
    """Test email service functionality"""
    
    @pytest.fixture
    def email_service(self):
        """Create email service instance"""
        return EmailService()
    
    @pytest.fixture
    def mock_smtp(self):
        """Create mock SMTP server"""
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value = mock_server
            yield mock_server
    
    @pytest.fixture
    def mock_smtp_ssl(self):
        """Create mock SMTP SSL server"""
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl_class:
            mock_server = MagicMock()
            mock_smtp_ssl_class.return_value = mock_server
            yield mock_server
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for email configuration"""
        settings = MagicMock()
        settings.smtp_server = "smtp.example.com"
        settings.smtp_port = 587
        settings.smtp_username = "test@example.com"
        settings.smtp_password = "password123"
        settings.smtp_use_tls = True
        settings.email_from = "noreply@example.com"
        return settings
    
    # Basic Email Sending Tests
    
    @pytest.mark.asyncio
    async def test_send_email_with_tls(self, email_service, mock_smtp, mock_settings):
        """Test sending email with TLS"""
        # Setup
        with patch('services.email_service.settings', mock_settings):
            # Test
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML content</p>",
                text_content="Test text content"
            )
        
        # Verify
        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with(
            mock_settings.smtp_username,
            mock_settings.smtp_password
        )
        mock_smtp.send_message.assert_called_once()
        mock_smtp.quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_with_ssl(self, email_service, mock_smtp_ssl, mock_settings):
        """Test sending email with SSL"""
        # Setup
        mock_settings.smtp_use_tls = False
        
        with patch('services.email_service.settings', mock_settings):
            # Test
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML content</p>"
            )
        
        # Verify
        assert result is True
        mock_smtp_ssl.login.assert_called_once()
        mock_smtp_ssl.send_message.assert_called_once()
        mock_smtp_ssl.quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_failure(self, email_service, mock_settings):
        """Test email sending failure"""
        # Setup
        with patch('services.email_service.settings', mock_settings):
            with patch('smtplib.SMTP') as mock_smtp_class:
                mock_smtp_class.side_effect = smtplib.SMTPException("Connection failed")
                
                # Test
                result = await email_service.send_email(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    html_content="<p>Test content</p>"
                )
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_email_message_construction(self, email_service, mock_smtp, mock_settings):
        """Test email message construction"""
        # Setup
        captured_message = None
        
        def capture_message(msg):
            nonlocal captured_message
            captured_message = msg
        
        mock_smtp.send_message.side_effect = capture_message
        
        with patch('services.email_service.settings', mock_settings):
            # Test
            await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>HTML content</p>",
                text_content="Text content"
            )
        
        # Verify message structure
        assert captured_message is not None
        assert captured_message["Subject"] == "Test Subject"
        assert captured_message["To"] == "recipient@example.com"
        assert "MAMS <noreply@example.com>" in captured_message["From"]
    
    # Verification Email Tests
    
    @pytest.mark.asyncio
    async def test_send_verification_email_success(self, email_service, mock_smtp, mock_settings):
        """Test sending verification email successfully"""
        # Setup
        with patch('services.email_service.settings', mock_settings):
            with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True
                
                # Test
                result = await email_service.send_verification_email(
                    to_email="user@example.com",
                    first_name="John",
                    verification_token="abc123token"
                )
        
        # Verify
        assert result is True
        mock_send.assert_called_once()
        
        # Check email content
        call_args = mock_send.call_args
        assert call_args[0][0] == "user@example.com"
        assert call_args[0][1] == "Please verify your MAMS account"
        assert "John" in call_args[0][2]  # HTML content
        assert "abc123token" in call_args[0][2]
        assert "John" in call_args[0][3]  # Text content
        assert "abc123token" in call_args[0][3]
    
    @pytest.mark.asyncio
    async def test_send_verification_email_content(self, email_service):
        """Test verification email content generation"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Test
            await email_service.send_verification_email(
                to_email="user@example.com",
                first_name="Jane",
                verification_token="xyz789token"
            )
        
        # Verify content
        html_content = mock_send.call_args[0][2]
        text_content = mock_send.call_args[0][3]
        
        # HTML content checks
        assert "Hi Jane" in html_content
        assert "xyz789token" in html_content
        assert "Verify Email Address" in html_content
        assert "24 hours" in html_content
        
        # Text content checks
        assert "Hi Jane" in text_content
        assert "xyz789token" in text_content
        assert "24 hours" in text_content
    
    # Password Reset Email Tests
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(self, email_service):
        """Test sending password reset email successfully"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Test
            result = await email_service.send_password_reset_email(
                to_email="user@example.com",
                first_name="Bob",
                reset_token="reset123token"
            )
        
        # Verify
        assert result is True
        mock_send.assert_called_once()
        
        # Check email details
        call_args = mock_send.call_args
        assert call_args[0][0] == "user@example.com"
        assert call_args[0][1] == "Reset your MAMS password"
        assert "Bob" in call_args[0][2]
        assert "reset123token" in call_args[0][2]
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email_content(self, email_service):
        """Test password reset email content generation"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Test
            await email_service.send_password_reset_email(
                to_email="user@example.com",
                first_name="Alice",
                reset_token="resetABCtoken"
            )
        
        # Verify content
        html_content = mock_send.call_args[0][2]
        text_content = mock_send.call_args[0][3]
        
        # HTML content checks
        assert "Hi Alice" in html_content
        assert "resetABCtoken" in html_content
        assert "Reset Password" in html_content
        assert "1 hour" in html_content
        assert "warning" in html_content  # Warning section
        
        # Text content checks
        assert "Hi Alice" in text_content
        assert "resetABCtoken" in text_content
        assert "1 hour" in text_content
    
    # Welcome Email Tests
    
    @pytest.mark.asyncio
    async def test_send_welcome_email_with_organization(self, email_service):
        """Test sending welcome email with organization"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Test
            result = await email_service.send_welcome_email(
                to_email="user@example.com",
                first_name="Charlie",
                organization="Tech Corp"
            )
        
        # Verify
        assert result is True
        
        # Check content
        html_content = mock_send.call_args[0][2]
        text_content = mock_send.call_args[0][3]
        
        assert "Hi Charlie" in html_content
        assert "Tech Corp" in html_content
        assert "Welcome to Tech Corp's media management system" in text_content
        assert "Get Started:" in html_content
        assert "Upload and organize" in html_content
    
    @pytest.mark.asyncio
    async def test_send_welcome_email_without_organization(self, email_service):
        """Test sending welcome email without organization"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Test
            result = await email_service.send_welcome_email(
                to_email="user@example.com",
                first_name="David",
                organization=None
            )
        
        # Verify
        assert result is True
        
        # Check content doesn't include organization
        html_content = mock_send.call_args[0][2]
        assert "Hi David" in html_content
        assert "Welcome to 's media management system" not in html_content
    
    # Account Activation Email Tests
    
    @pytest.mark.asyncio
    async def test_send_account_activation_email_success(self, email_service):
        """Test sending account activation email"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Test
            result = await email_service.send_account_activation_email(
                to_email="user@example.com",
                first_name="Eve",
                admin_name="Admin User"
            )
        
        # Verify
        assert result is True
        
        # Check content
        call_args = mock_send.call_args
        assert call_args[0][0] == "user@example.com"
        assert call_args[0][1] == "Your MAMS account has been activated"
        
        html_content = call_args[0][2]
        text_content = call_args[0][3]
        
        assert "Hi Eve" in html_content
        assert "Admin User" in html_content
        assert "account has been activated" in html_content
        assert "Login to MAMS" in html_content
    
    # Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_send_verification_email_failure(self, email_service):
        """Test verification email sending failure"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Email service error")
            
            # Test
            result = await email_service.send_verification_email(
                to_email="user@example.com",
                first_name="Failed",
                verification_token="token"
            )
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email_failure(self, email_service):
        """Test password reset email sending failure"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            
            # Test
            result = await email_service.send_password_reset_email(
                to_email="user@example.com",
                first_name="Failed",
                reset_token="token"
            )
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_welcome_email_failure(self, email_service):
        """Test welcome email sending failure"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("SMTP error")
            
            # Test
            result = await email_service.send_welcome_email(
                to_email="user@example.com",
                first_name="Failed"
            )
        
        # Verify
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_account_activation_email_failure(self, email_service):
        """Test account activation email sending failure"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            
            # Test
            result = await email_service.send_account_activation_email(
                to_email="user@example.com",
                first_name="Failed",
                admin_name="Admin"
            )
        
        # Verify
        assert result is False
    
    # Template Rendering Tests
    
    @pytest.mark.asyncio
    async def test_email_template_escaping(self, email_service):
        """Test proper HTML escaping in email templates"""
        # Setup
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Test with potentially unsafe input
            await email_service.send_verification_email(
                to_email="user@example.com",
                first_name="<script>alert('xss')</script>",
                verification_token="token"
            )
        
        # Verify - should escape HTML
        html_content = mock_send.call_args[0][2]
        assert "<script>" not in html_content
        assert "&lt;script&gt;" in html_content or "alert" not in html_content