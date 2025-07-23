"""
Request Validation and Sanitization

Comprehensive input validation and sanitization to protect against
security vulnerabilities and ensure data integrity.
"""

import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from email_validator import validate_email, EmailNotValidError
from pydantic import BaseModel, Field, validator
import logging

from core.exceptions import ValidationException
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RequestValidationConfig(BaseModel):
    """Configuration for request validation"""
    
    # String validation
    max_string_length: int = Field(default=10000, description="Maximum string length")
    max_text_length: int = Field(default=100000, description="Maximum text field length")
    min_password_length: int = Field(default=8, description="Minimum password length")
    
    # Request limits
    max_json_size: int = Field(default=10 * 1024 * 1024, description="Maximum JSON payload size (10MB)")
    max_form_fields: int = Field(default=100, description="Maximum form fields")
    max_query_params: int = Field(default=50, description="Maximum query parameters")
    max_header_size: int = Field(default=8192, description="Maximum header size")
    
    # File validation
    max_filename_length: int = Field(default=255, description="Maximum filename length")
    allowed_file_extensions: List[str] = Field(
        default_factory=lambda: [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',  # Images
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',    # Video
            '.mp3', '.wav', '.aac', '.ogg', '.flac',          # Audio
            '.pdf', '.doc', '.docx', '.txt', '.rtf',          # Documents
            '.zip', '.rar', '.7z', '.tar', '.gz'             # Archives
        ],
        description="Allowed file extensions"
    )
    
    # Security patterns
    blocked_patterns: List[str] = Field(
        default_factory=lambda: [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                # JavaScript URLs
            r'vbscript:',                 # VBScript URLs
            r'on\w+\s*=',                # Event handlers
            r'\beval\s*\(',             # eval() calls
            r'\bexec\s*\(',             # exec() calls
            r'\\x[0-9a-fA-F]{2}',        # Hex encoding
            r'\\u[0-9a-fA-F]{4}',        # Unicode encoding
            r'\\[0-7]{1,3}',             # Octal encoding
            r'\\r|\\n|\\t',           # Control characters
            r'\\0',                      # Null bytes
            r'\\x00',                    # Null bytes (hex)
            r'%00',                       # Null bytes (URL encoded)
            r'\.\.[\\/]',              # Directory traversal
            r'[\\/]etc[\\/]passwd',     # Unix passwd file
            r'[\\/]windows[\\/]system32', # Windows system dir
            r'<\?php',                   # PHP tags
            r'<%.*%>',                   # ASP tags
            r'\${.*}',                   # Expression language
            r'\\$\{.*\}',              # EL expressions
            r'\bUNION\b.*\bSELECT\b',   # SQL injection
            r'\bDROP\b.*\bTABLE\b',     # SQL injection
            r'\bINSERT\b.*\bINTO\b',    # SQL injection
            r'\bUPDATE\b.*\bSET\b',     # SQL injection
            r'\bDELETE\b.*\bFROM\b',    # SQL injection
            r'\-\-',                     # SQL comments
            r'/\*.*\*/',                # SQL comments
            r'\bxp_cmdshell\b',         # SQL Server command execution
            r'\bsp_executesql\b',       # SQL Server stored procedure
        ],
        description="Blocked security patterns"
    )
    
    # Rate limiting for validation
    validation_rate_limit: int = Field(default=1000, description="Validation operations per minute")
    
    # Logging
    log_blocked_requests: bool = Field(default=True, description="Log blocked requests")
    log_sanitization: bool = Field(default=False, description="Log sanitization operations")


class InputSanitizer:
    """Input sanitization utilities"""
    
    def __init__(self, config: RequestValidationConfig):
        self.config = config
        self.blocked_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in config.blocked_patterns]
    
    def sanitize_string(self, value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize a string value
        
        Args:
            value: Input string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationException("Value must be a string")
        
        # Check length
        max_len = max_length or self.config.max_string_length
        if len(value) > max_len:
            raise ValidationException(f"String too long (max {max_len} characters)")
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if pattern.search(value):
                if self.config.log_blocked_requests:
                    logger.warning(f"Blocked pattern detected: {pattern.pattern}")
                raise ValidationException("Input contains blocked content")
        
        # HTML encode to prevent XSS
        sanitized = html.escape(value)
        
        # Remove control characters except common whitespace
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', sanitized)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        if self.config.log_sanitization and sanitized != value:
            logger.debug(f"Sanitized string: {value[:50]}... -> {sanitized[:50]}...")
        
        return sanitized
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename
        
        Args:
            filename: Input filename
            
        Returns:
            Sanitized filename
            
        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(filename, str):
            raise ValidationException("Filename must be a string")
        
        if len(filename) > self.config.max_filename_length:
            raise ValidationException(f"Filename too long (max {self.config.max_filename_length} characters)")
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', filename)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Prevent reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
            'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
            'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = sanitized.split('.')[0].upper()
        if name_without_ext in reserved_names:
            raise ValidationException(f"Reserved filename: {filename}")
        
        # Check file extension
        if '.' in sanitized:
            ext = '.' + sanitized.split('.')[-1].lower()
            if ext not in self.config.allowed_file_extensions:
                raise ValidationException(f"File extension not allowed: {ext}")
        
        return sanitized
    
    def sanitize_url(self, url: str) -> str:
        """
        Sanitize a URL
        
        Args:
            url: Input URL
            
        Returns:
            Sanitized URL
            
        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(url, str):
            raise ValidationException("URL must be a string")
        
        # Parse URL
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            raise ValidationException(f"Invalid URL format: {e}")
        
        # Check scheme
        allowed_schemes = {'http', 'https', 'ftp', 'ftps'}
        if parsed.scheme.lower() not in allowed_schemes:
            raise ValidationException(f"URL scheme not allowed: {parsed.scheme}")
        
        # Check for dangerous patterns
        full_url = urllib.parse.urlunparse(parsed)
        for pattern in self.blocked_patterns:
            if pattern.search(full_url):
                raise ValidationException("URL contains blocked content")
        
        return full_url
    
    def sanitize_email(self, email: str) -> str:
        """
        Sanitize and validate an email address
        
        Args:
            email: Input email
            
        Returns:
            Sanitized email
            
        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(email, str):
            raise ValidationException("Email must be a string")
        
        try:
            # Use email-validator library
            valid_email = validate_email(email)
            return valid_email.email
        except EmailNotValidError as e:
            raise ValidationException(f"Invalid email format: {e}")
    
    def sanitize_ip_address(self, ip_address: str) -> str:
        """
        Sanitize and validate an IP address
        
        Args:
            ip_address: Input IP address
            
        Returns:
            Sanitized IP address
            
        Raises:
            ValidationException: If validation fails
        """
        if not isinstance(ip_address, str):
            raise ValidationException("IP address must be a string")
        
        try:
            # Try IPv4 first
            ipv4 = IPv4Address(ip_address)
            return str(ipv4)
        except AddressValueError:
            try:
                # Try IPv6
                ipv6 = IPv6Address(ip_address)
                return str(ipv6)
            except AddressValueError:
                raise ValidationException(f"Invalid IP address format: {ip_address}")
    
    def sanitize_json_value(self, value: Any, max_depth: int = 10) -> Any:
        """
        Recursively sanitize JSON values
        
        Args:
            value: JSON value to sanitize
            max_depth: Maximum nesting depth
            
        Returns:
            Sanitized value
            
        Raises:
            ValidationException: If validation fails
        """
        if max_depth <= 0:
            raise ValidationException("JSON structure too deeply nested")
        
        if isinstance(value, str):
            return self.sanitize_string(value)
        elif isinstance(value, dict):
            if len(value) > self.config.max_form_fields:
                raise ValidationException(f"Too many fields in object (max {self.config.max_form_fields})")
            return {k: self.sanitize_json_value(v, max_depth - 1) for k, v in value.items()}
        elif isinstance(value, list):
            if len(value) > self.config.max_form_fields:
                raise ValidationException(f"Too many items in array (max {self.config.max_form_fields})")
            return [self.sanitize_json_value(item, max_depth - 1) for item in value]
        elif isinstance(value, (int, float, bool)) or value is None:
            return value
        else:
            # Convert other types to string and sanitize
            return self.sanitize_string(str(value))


class RequestValidator:
    """Request validation utilities"""
    
    def __init__(self, config: RequestValidationConfig):
        self.config = config
        self.sanitizer = InputSanitizer(config)
    
    def validate_content_length(self, content_length: Optional[int]) -> None:
        """
        Validate request content length
        
        Args:
            content_length: Content length in bytes
            
        Raises:
            ValidationException: If validation fails
        """
        if content_length is not None and content_length > self.config.max_json_size:
            raise ValidationException(f"Request too large (max {self.config.max_json_size} bytes)")
    
    def validate_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and sanitize request headers
        
        Args:
            headers: Request headers
            
        Returns:
            Sanitized headers
            
        Raises:
            ValidationException: If validation fails
        """
        sanitized_headers = {}
        
        for name, value in headers.items():
            # Check header size
            if len(name) + len(value) > self.config.max_header_size:
                raise ValidationException(f"Header too large: {name}")
            
            # Sanitize header value
            try:
                sanitized_value = self.sanitizer.sanitize_string(value, self.config.max_header_size)
                sanitized_headers[name] = sanitized_value
            except ValidationException as e:
                if self.config.log_blocked_requests:
                    logger.warning(f"Blocked header {name}: {e}")
                # Skip problematic headers instead of failing the entire request
                continue
        
        return sanitized_headers
    
    def validate_query_params(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize query parameters
        
        Args:
            query_params: Query parameters
            
        Returns:
            Sanitized query parameters
            
        Raises:
            ValidationException: If validation fails
        """
        if len(query_params) > self.config.max_query_params:
            raise ValidationException(f"Too many query parameters (max {self.config.max_query_params})")
        
        sanitized_params = {}
        
        for name, value in query_params.items():
            # Sanitize parameter name
            sanitized_name = self.sanitizer.sanitize_string(name, 100)
            
            # Sanitize parameter value
            if isinstance(value, list):
                sanitized_value = [self.sanitizer.sanitize_string(str(v), 1000) for v in value]
            else:
                sanitized_value = self.sanitizer.sanitize_string(str(value), 1000)
            
            sanitized_params[sanitized_name] = sanitized_value
        
        return sanitized_params
    
    def validate_json_body(self, json_body: Any) -> Any:
        """
        Validate and sanitize JSON request body
        
        Args:
            json_body: JSON request body
            
        Returns:
            Sanitized JSON body
            
        Raises:
            ValidationException: If validation fails
        """
        if json_body is None:
            return None
        
        return self.sanitizer.sanitize_json_value(json_body)
    
    def validate_form_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize form data
        
        Args:
            form_data: Form data
            
        Returns:
            Sanitized form data
            
        Raises:
            ValidationException: If validation fails
        """
        if len(form_data) > self.config.max_form_fields:
            raise ValidationException(f"Too many form fields (max {self.config.max_form_fields})")
        
        sanitized_data = {}
        
        for name, value in form_data.items():
            # Sanitize field name
            sanitized_name = self.sanitizer.sanitize_string(name, 100)
            
            # Sanitize field value
            if isinstance(value, str):
                sanitized_value = self.sanitizer.sanitize_string(value)
            elif isinstance(value, list):
                sanitized_value = [self.sanitizer.sanitize_string(str(v)) for v in value]
            else:
                sanitized_value = self.sanitizer.sanitize_string(str(value))
            
            sanitized_data[sanitized_name] = sanitized_value
        
        return sanitized_data
    
    def validate_file_upload(self, filename: str, content_type: str, file_size: int) -> None:
        """
        Validate file upload
        
        Args:
            filename: Uploaded filename
            content_type: File content type
            file_size: File size in bytes
            
        Raises:
            ValidationException: If validation fails
        """
        # Validate filename
        sanitized_filename = self.sanitizer.sanitize_filename(filename)
        
        # Validate file size
        if file_size > self.config.max_json_size:
            raise ValidationException(f"File too large (max {self.config.max_json_size} bytes)")
        
        # Validate content type
        if content_type:
            # Basic content type validation
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*$', content_type):
                raise ValidationException(f"Invalid content type: {content_type}")


def get_validator() -> RequestValidator:
    """Get request validator instance"""
    config = RequestValidationConfig()
    return RequestValidator(config)


def get_sanitizer() -> InputSanitizer:
    """Get input sanitizer instance"""
    config = RequestValidationConfig()
    return InputSanitizer(config)
