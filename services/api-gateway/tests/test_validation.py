"""
Tests for Request Validation and Sanitization

Comprehensive tests for input validation, sanitization, and security middleware.
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import json

from core.validation import (
    RequestValidationConfig,
    InputSanitizer,
    RequestValidator,
    get_sanitizer,
    get_validator
)
from core.validation_middleware import (
    ValidationMiddleware,
    ContentSecurityMiddleware,
    RequestSizeMiddleware
)
from core.validation_utils import (
    PaginationParams,
    SortingParams,
    FilterParams,
    UUIDParam,
    SlugParam,
    validate_uuid_param,
    validate_email_param,
    validate_url_param
)
from core.exceptions import ValidationException


class TestRequestValidationConfig:
    """Test cases for validation configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = RequestValidationConfig()
        
        assert config.max_string_length == 10000
        assert config.max_text_length == 100000
        assert config.min_password_length == 8
        assert config.max_json_size == 10 * 1024 * 1024
        assert config.max_form_fields == 100
        assert config.max_query_params == 50
        assert config.max_header_size == 8192
        assert config.max_filename_length == 255
        assert len(config.allowed_file_extensions) > 0
        assert len(config.blocked_patterns) > 0
        assert config.validation_rate_limit == 1000
        assert config.log_blocked_requests is True
        assert config.log_sanitization is False
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = RequestValidationConfig(
            max_string_length=5000,
            max_json_size=5 * 1024 * 1024,
            log_sanitization=True
        )
        
        assert config.max_string_length == 5000
        assert config.max_json_size == 5 * 1024 * 1024
        assert config.log_sanitization is True


class TestInputSanitizer:
    """Test cases for input sanitization"""
    
    @pytest.fixture
    def sanitizer(self):
        """Create sanitizer instance"""
        config = RequestValidationConfig()
        return InputSanitizer(config)
    
    def test_sanitize_string_basic(self, sanitizer):
        """Test basic string sanitization"""
        result = sanitizer.sanitize_string("Hello World")
        assert result == "Hello World"
    
    def test_sanitize_string_html_escape(self, sanitizer):
        """Test HTML escaping"""
        result = sanitizer.sanitize_string("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
    
    def test_sanitize_string_blocked_patterns(self, sanitizer):
        """Test blocked pattern detection"""
        with pytest.raises(ValidationException, match="blocked content"):
            sanitizer.sanitize_string("javascript:alert('xss')")
        
        with pytest.raises(ValidationException, match="blocked content"):
            sanitizer.sanitize_string("<script>alert('xss')</script>")
        
        with pytest.raises(ValidationException, match="blocked content"):
            sanitizer.sanitize_string("UNION SELECT * FROM users")
    
    def test_sanitize_string_length_validation(self, sanitizer):
        """Test string length validation"""
        with pytest.raises(ValidationException, match="too long"):
            sanitizer.sanitize_string("a" * 10001)
        
        # Should work with custom length
        result = sanitizer.sanitize_string("a" * 100, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_string_control_characters(self, sanitizer):
        """Test control character removal"""
        result = sanitizer.sanitize_string("Hello\x00World\x1F")
        assert "\x00" not in result
        assert "\x1F" not in result
        assert "HelloWorld" in result
    
    def test_sanitize_string_whitespace_normalization(self, sanitizer):
        """Test whitespace normalization"""
        result = sanitizer.sanitize_string("  Hello\t\n  World  ")
        assert result == "Hello World"
    
    def test_sanitize_string_non_string_input(self, sanitizer):
        """Test non-string input validation"""
        with pytest.raises(ValidationException, match="must be a string"):
            sanitizer.sanitize_string(123)
        
        with pytest.raises(ValidationException, match="must be a string"):
            sanitizer.sanitize_string(None)
    
    def test_sanitize_filename_basic(self, sanitizer):
        """Test basic filename sanitization"""
        result = sanitizer.sanitize_filename("document.pdf")
        assert result == "document.pdf"
    
    def test_sanitize_filename_dangerous_chars(self, sanitizer):
        """Test dangerous character removal"""
        result = sanitizer.sanitize_filename("doc<>:?*|\x00ument.pdf")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "?" not in result
        assert "*" not in result
        assert "|" not in result
        assert "\x00" not in result
        assert "document.pdf" in result
    
    def test_sanitize_filename_reserved_names(self, sanitizer):
        """Test reserved filename validation"""
        with pytest.raises(ValidationException, match="Reserved filename"):
            sanitizer.sanitize_filename("CON.txt")
        
        with pytest.raises(ValidationException, match="Reserved filename"):
            sanitizer.sanitize_filename("aux.pdf")
    
    def test_sanitize_filename_extension_validation(self, sanitizer):
        """Test file extension validation"""
        # Valid extension
        result = sanitizer.sanitize_filename("document.pdf")
        assert result == "document.pdf"
        
        # Invalid extension
        with pytest.raises(ValidationException, match="not allowed"):
            sanitizer.sanitize_filename("malware.exe")
    
    def test_sanitize_filename_length_validation(self, sanitizer):
        """Test filename length validation"""
        with pytest.raises(ValidationException, match="too long"):
            sanitizer.sanitize_filename("a" * 256 + ".pdf")
    
    def test_sanitize_url_basic(self, sanitizer):
        """Test basic URL sanitization"""
        result = sanitizer.sanitize_url("https://example.com/path")
        assert result == "https://example.com/path"
    
    def test_sanitize_url_invalid_scheme(self, sanitizer):
        """Test invalid URL scheme validation"""
        with pytest.raises(ValidationException, match="scheme not allowed"):
            sanitizer.sanitize_url("javascript:alert('xss')")
        
        with pytest.raises(ValidationException, match="scheme not allowed"):
            sanitizer.sanitize_url("data:text/html,<script>alert('xss')</script>")
    
    def test_sanitize_url_blocked_content(self, sanitizer):
        """Test blocked content in URLs"""
        with pytest.raises(ValidationException, match="blocked content"):
            sanitizer.sanitize_url("https://example.com/<script>alert('xss')</script>")
    
    def test_sanitize_url_invalid_format(self, sanitizer):
        """Test invalid URL format"""
        with pytest.raises(ValidationException, match="Invalid URL format"):
            sanitizer.sanitize_url("not a url")
    
    def test_sanitize_email_valid(self, sanitizer):
        """Test valid email sanitization"""
        result = sanitizer.sanitize_email("test@example.com")
        assert result == "test@example.com"
        
        # Test with different valid formats
        result = sanitizer.sanitize_email("Test.Email+123@Example.COM")
        assert result.lower() == "test.email+123@example.com"
    
    def test_sanitize_email_invalid(self, sanitizer):
        """Test invalid email validation"""
        with pytest.raises(ValidationException, match="Invalid email format"):
            sanitizer.sanitize_email("invalid-email")
        
        with pytest.raises(ValidationException, match="Invalid email format"):
            sanitizer.sanitize_email("test@")
        
        with pytest.raises(ValidationException, match="Invalid email format"):
            sanitizer.sanitize_email("@example.com")
    
    def test_sanitize_ip_address_valid(self, sanitizer):
        """Test valid IP address sanitization"""
        # IPv4
        result = sanitizer.sanitize_ip_address("192.168.1.1")
        assert result == "192.168.1.1"
        
        # IPv6
        result = sanitizer.sanitize_ip_address("2001:db8::1")
        assert result == "2001:db8::1"
    
    def test_sanitize_ip_address_invalid(self, sanitizer):
        """Test invalid IP address validation"""
        with pytest.raises(ValidationException, match="Invalid IP address format"):
            sanitizer.sanitize_ip_address("256.256.256.256")
        
        with pytest.raises(ValidationException, match="Invalid IP address format"):
            sanitizer.sanitize_ip_address("not-an-ip")
    
    def test_sanitize_json_value_nested(self, sanitizer):
        """Test nested JSON value sanitization"""
        data = {
            "string": "<script>alert('xss')</script>",
            "number": 123,
            "boolean": True,
            "null": None,
            "array": ["item1", "<script>alert('xss')</script>"],
            "nested": {
                "inner": "<script>alert('xss')</script>"
            }
        }
        
        result = sanitizer.sanitize_json_value(data)
        
        assert "&lt;script&gt;" in result["string"]
        assert result["number"] == 123
        assert result["boolean"] is True
        assert result["null"] is None
        assert "&lt;script&gt;" in result["array"][1]
        assert "&lt;script&gt;" in result["nested"]["inner"]
    
    def test_sanitize_json_value_max_depth(self, sanitizer):
        """Test JSON depth limitation"""
        # Create deeply nested structure
        data = {"level1": {"level2": {"level3": {"level4": {"level5": {"level6": {"level7": {"level8": {"level9": {"level10": {"level11": "too deep"}}}}}}}}}}
        
        with pytest.raises(ValidationException, match="too deeply nested"):
            sanitizer.sanitize_json_value(data)
    
    def test_sanitize_json_value_too_many_fields(self, sanitizer):
        """Test JSON field count limitation"""
        data = {f"field{i}": f"value{i}" for i in range(101)}
        
        with pytest.raises(ValidationException, match="Too many fields"):
            sanitizer.sanitize_json_value(data)
    
    def test_sanitize_json_value_too_many_array_items(self, sanitizer):
        """Test JSON array size limitation"""
        data = [f"item{i}" for i in range(101)]
        
        with pytest.raises(ValidationException, match="Too many items"):
            sanitizer.sanitize_json_value(data)


class TestRequestValidator:
    """Test cases for request validation"""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        config = RequestValidationConfig()
        return RequestValidator(config)
    
    def test_validate_content_length_valid(self, validator):
        """Test valid content length"""
        # Should not raise exception
        validator.validate_content_length(1024)
        validator.validate_content_length(None)
    
    def test_validate_content_length_too_large(self, validator):
        """Test content length too large"""
        with pytest.raises(ValidationException, match="Request too large"):
            validator.validate_content_length(20 * 1024 * 1024)
    
    def test_validate_headers_basic(self, validator):
        """Test basic header validation"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token",
            "User-Agent": "Test Client"
        }
        
        result = validator.validate_headers(headers)
        assert "Content-Type" in result
        assert "Authorization" in result
        assert "User-Agent" in result
    
    def test_validate_headers_too_large(self, validator):
        """Test header size validation"""
        headers = {
            "Large-Header": "a" * 10000
        }
        
        with pytest.raises(ValidationException, match="Header too large"):
            validator.validate_headers(headers)
    
    def test_validate_headers_malicious_content(self, validator):
        """Test header with malicious content"""
        headers = {
            "X-Custom-Header": "<script>alert('xss')</script>"
        }
        
        # Should skip problematic headers
        result = validator.validate_headers(headers)
        assert "X-Custom-Header" not in result
    
    def test_validate_query_params_basic(self, validator):
        """Test basic query parameter validation"""
        params = {
            "page": "1",
            "limit": "20",
            "search": "test query"
        }
        
        result = validator.validate_query_params(params)
        assert "page" in result
        assert "limit" in result
        assert "search" in result
    
    def test_validate_query_params_too_many(self, validator):
        """Test too many query parameters"""
        params = {f"param{i}": f"value{i}" for i in range(51)}
        
        with pytest.raises(ValidationException, match="Too many query parameters"):
            validator.validate_query_params(params)
    
    def test_validate_query_params_list_values(self, validator):
        """Test query parameters with list values"""
        params = {
            "tags": ["tag1", "tag2", "tag3"]
        }
        
        result = validator.validate_query_params(params)
        assert "tags" in result
        assert isinstance(result["tags"], list)
        assert len(result["tags"]) == 3
    
    def test_validate_json_body_basic(self, validator):
        """Test basic JSON body validation"""
        json_body = {
            "name": "Test",
            "value": 123,
            "active": True
        }
        
        result = validator.validate_json_body(json_body)
        assert result["name"] == "Test"
        assert result["value"] == 123
        assert result["active"] is True
    
    def test_validate_json_body_none(self, validator):
        """Test None JSON body"""
        result = validator.validate_json_body(None)
        assert result is None
    
    def test_validate_form_data_basic(self, validator):
        """Test basic form data validation"""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "active": "true"
        }
        
        result = validator.validate_form_data(form_data)
        assert "username" in result
        assert "email" in result
        assert "active" in result
    
    def test_validate_form_data_too_many_fields(self, validator):
        """Test too many form fields"""
        form_data = {f"field{i}": f"value{i}" for i in range(101)}
        
        with pytest.raises(ValidationException, match="Too many form fields"):
            validator.validate_form_data(form_data)
    
    def test_validate_file_upload_basic(self, validator):
        """Test basic file upload validation"""
        # Should not raise exception
        validator.validate_file_upload("document.pdf", "application/pdf", 1024)
    
    def test_validate_file_upload_too_large(self, validator):
        """Test file upload size validation"""
        with pytest.raises(ValidationException, match="File too large"):
            validator.validate_file_upload("large.pdf", "application/pdf", 20 * 1024 * 1024)
    
    def test_validate_file_upload_invalid_content_type(self, validator):
        """Test file upload content type validation"""
        with pytest.raises(ValidationException, match="Invalid content type"):
            validator.validate_file_upload("test.pdf", "<script>alert('xss')</script>", 1024)


class TestValidationUtils:
    """Test cases for validation utilities"""
    
    def test_pagination_params_valid(self):
        """Test valid pagination parameters"""
        params = PaginationParams(page=1, limit=20)
        assert params.page == 1
        assert params.limit == 20
        assert params.offset == 0
        
        params = PaginationParams(page=2, limit=10)
        assert params.offset == 10
    
    def test_pagination_params_invalid(self):
        """Test invalid pagination parameters"""
        with pytest.raises(ValueError):
            PaginationParams(page=0, limit=20)
        
        with pytest.raises(ValueError):
            PaginationParams(page=1, limit=0)
        
        with pytest.raises(ValueError):
            PaginationParams(page=1, limit=1001)
    
    def test_sorting_params_valid(self):
        """Test valid sorting parameters"""
        params = SortingParams(sort_by="created_at", sort_order="desc")
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"
    
    def test_sorting_params_invalid_order(self):
        """Test invalid sort order"""
        with pytest.raises(ValueError):
            SortingParams(sort_by="created_at", sort_order="invalid")
    
    def test_sorting_params_invalid_field(self):
        """Test invalid sort field"""
        with pytest.raises(ValueError):
            SortingParams(sort_by="invalid-field-name")
    
    def test_filter_params_valid(self):
        """Test valid filter parameters"""
        from datetime import datetime
        
        params = FilterParams(
            search="test query",
            status="active",
            created_after=datetime.now(),
            created_before=datetime.now()
        )
        
        assert params.search == "test query"
        assert params.status == "active"
        assert params.created_after is not None
        assert params.created_before is not None
    
    def test_filter_params_search_too_short(self):
        """Test search query too short"""
        with pytest.raises(ValueError, match="at least 2 characters"):
            FilterParams(search="a")
    
    def test_uuid_param_valid(self):
        """Test valid UUID parameter"""
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        param = UUIDParam(id=uuid_str)
        assert param.id == uuid_str
    
    def test_uuid_param_invalid(self):
        """Test invalid UUID parameter"""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            UUIDParam(id="invalid-uuid")
    
    def test_slug_param_valid(self):
        """Test valid slug parameter"""
        param = SlugParam(slug="valid-slug-123")
        assert param.slug == "valid-slug-123"
    
    def test_slug_param_invalid(self):
        """Test invalid slug parameter"""
        with pytest.raises(ValueError, match="Invalid slug format"):
            SlugParam(slug="Invalid_Slug")
    
    def test_validate_uuid_param_function(self):
        """Test UUID validation function"""
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        result = validate_uuid_param(uuid_str)
        assert result == uuid_str
        
        with pytest.raises(HTTPException):
            validate_uuid_param("invalid-uuid")
    
    def test_validate_email_param_function(self):
        """Test email validation function"""
        with patch('core.validation_utils.get_sanitizer') as mock_sanitizer:
            mock_sanitizer.return_value.sanitize_email.return_value = "test@example.com"
            
            result = validate_email_param("test@example.com")
            assert result == "test@example.com"
    
    def test_validate_url_param_function(self):
        """Test URL validation function"""
        with patch('core.validation_utils.get_sanitizer') as mock_sanitizer:
            mock_sanitizer.return_value.sanitize_url.return_value = "https://example.com"
            
            result = validate_url_param("https://example.com")
            assert result == "https://example.com"


class TestValidationMiddleware:
    """Test cases for validation middleware"""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.post("/test")
        async def test_post_endpoint(request: Request):
            return {"message": "success"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client with validation middleware"""
        app.add_middleware(ValidationMiddleware)
        return TestClient(app)
    
    def test_middleware_skip_excluded_paths(self, app):
        """Test middleware skips excluded paths"""
        app.add_middleware(ValidationMiddleware)
        client = TestClient(app)
        
        # Health check should be skipped
        response = client.get("/health")
        # Should get 404 since endpoint doesn't exist, but not validation error
        assert response.status_code == 404
    
    def test_middleware_skip_options_method(self, app):
        """Test middleware skips OPTIONS method"""
        app.add_middleware(ValidationMiddleware)
        client = TestClient(app)
        
        response = client.options("/test")
        # Should get 405 since OPTIONS not allowed, but not validation error
        assert response.status_code == 405
    
    def test_middleware_valid_request(self, client):
        """Test middleware with valid request"""
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    def test_middleware_content_length_validation(self, client):
        """Test content length validation"""
        # Mock large content length
        large_data = "x" * (20 * 1024 * 1024)  # 20MB
        
        response = client.post("/test", data=large_data)
        assert response.status_code == 413  # Request Entity Too Large
    
    def test_middleware_json_validation(self, client):
        """Test JSON validation"""
        valid_json = {"key": "value"}
        response = client.post("/test", json=valid_json)
        assert response.status_code == 200
    
    def test_middleware_malicious_json(self, client):
        """Test malicious JSON validation"""
        malicious_json = {"key": "<script>alert('xss')</script>"}
        response = client.post("/test", json=malicious_json)
        # Should sanitize but not block
        assert response.status_code == 200
    
    def test_content_security_middleware(self, app):
        """Test content security middleware"""
        app.add_middleware(ContentSecurityMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        # Check security headers
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    def test_request_size_middleware(self, app):
        """Test request size middleware"""
        app.add_middleware(RequestSizeMiddleware, max_size=1024)
        client = TestClient(app)
        
        # Small request should pass
        response = client.post("/test", data="small data")
        assert response.status_code == 200
        
        # Large request should be blocked
        large_data = "x" * 2048
        response = client.post("/test", data=large_data, headers={"content-length": "2048"})
        assert response.status_code == 413


class TestValidationIntegration:
    """Integration tests for validation system"""
    
    def test_full_validation_pipeline(self):
        """Test complete validation pipeline"""
        app = FastAPI()
        
        @app.post("/api/v1/test")
        async def test_endpoint(request: Request):
            from core.validation_middleware import (
                get_sanitized_json,
                get_sanitized_query_params,
                get_sanitized_headers
            )
            
            return {
                "json": get_sanitized_json(request),
                "query_params": get_sanitized_query_params(request),
                "headers": get_sanitized_headers(request)
            }
        
        # Add middleware stack
        app.add_middleware(ValidationMiddleware)
        app.add_middleware(ContentSecurityMiddleware)
        app.add_middleware(RequestSizeMiddleware)
        
        client = TestClient(app)
        
        # Test with mixed clean and malicious data
        response = client.post(
            "/api/v1/test?search=clean&malicious=<script>alert('xss')</script>",
            json={"clean": "data", "malicious": "<script>alert('xss')</script>"},
            headers={"X-Custom": "<script>alert('xss')</script>"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that malicious content was sanitized
        assert "&lt;script&gt;" in str(data["json"])
        assert "&lt;script&gt;" in str(data["query_params"])
        
        # Check security headers
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
    
    def test_validation_error_handling(self):
        """Test validation error handling"""
        app = FastAPI()
        
        @app.post("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        app.add_middleware(ValidationMiddleware)
        client = TestClient(app)
        
        # Test with blocked pattern
        response = client.post(
            "/test",
            json={"data": "javascript:alert('xss')"}
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_validation_performance(self):
        """Test validation performance"""
        import time
        
        app = FastAPI()
        
        @app.post("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        app.add_middleware(ValidationMiddleware)
        client = TestClient(app)
        
        # Test with moderately complex data
        test_data = {
            "users": [
                {"name": f"User {i}", "email": f"user{i}@example.com"}
                for i in range(100)
            ],
            "metadata": {
                "description": "Test data for performance testing",
                "tags": [f"tag{i}" for i in range(50)]
            }
        }
        
        start_time = time.time()
        response = client.post("/test", json=test_data)
        end_time = time.time()
        
        assert response.status_code == 200
        # Validation should complete in reasonable time (< 1 second)
        assert (end_time - start_time) < 1.0
