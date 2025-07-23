"""
Tests for OpenAPI Configuration

Comprehensive tests for OpenAPI/Swagger documentation configuration,
including security schemes, examples, and endpoint behavior.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from core.openapi import (
    get_openapi_tags,
    get_openapi_security_schemes,
    get_openapi_servers,
    get_openapi_info,
    get_openapi_examples,
    customize_openapi_schema,
    setup_openapi_docs,
    configure_openapi_security,
    add_response_examples,
    setup_openapi_configuration
)
from core.config import get_settings


class TestOpenAPIConfiguration:
    """Test cases for OpenAPI configuration"""
    
    def test_get_openapi_tags(self):
        """Test OpenAPI tags generation"""
        tags = get_openapi_tags()
        
        assert isinstance(tags, list)
        assert len(tags) > 0
        
        # Check required tags
        tag_names = [tag["name"] for tag in tags]
        assert "health" in tag_names
        assert "auth" in tag_names
        assert "users" in tag_names
        assert "assets" in tag_names
        assert "admin" in tag_names
        
        # Check tag structure
        for tag in tags:
            assert "name" in tag
            assert "description" in tag
            assert isinstance(tag["name"], str)
            assert isinstance(tag["description"], str)
    
    def test_get_openapi_security_schemes(self):
        """Test OpenAPI security schemes"""
        schemes = get_openapi_security_schemes()
        
        assert isinstance(schemes, dict)
        assert "BearerAuth" in schemes
        assert "ApiKeyAuth" in schemes
        assert "OAuth2" in schemes
        
        # Check Bearer auth scheme
        bearer_auth = schemes["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"
        
        # Check API key scheme
        api_key_auth = schemes["ApiKeyAuth"]
        assert api_key_auth["type"] == "apiKey"
        assert api_key_auth["in"] == "header"
        assert api_key_auth["name"] == "X-API-Key"
        
        # Check OAuth2 scheme
        oauth2 = schemes["OAuth2"]
        assert oauth2["type"] == "oauth2"
        assert "flows" in oauth2
        assert "authorizationCode" in oauth2["flows"]
    
    def test_get_openapi_servers(self):
        """Test OpenAPI servers configuration"""
        servers = get_openapi_servers()
        
        assert isinstance(servers, list)
        assert len(servers) > 0
        
        # Check localhost server
        localhost_server = next((s for s in servers if "localhost" in s["url"]), None)
        assert localhost_server is not None
        assert localhost_server["description"] == "Development server"
        
        # Check server structure
        for server in servers:
            assert "url" in server
            assert "description" in server
            assert isinstance(server["url"], str)
            assert isinstance(server["description"], str)
    
    def test_get_openapi_info(self):
        """Test OpenAPI info configuration"""
        info = get_openapi_info()
        
        assert isinstance(info, dict)
        assert "title" in info
        assert "description" in info
        assert "version" in info
        assert "contact" in info
        assert "license" in info
        assert "termsOfService" in info
        
        # Check contact information
        contact = info["contact"]
        assert "name" in contact
        assert "email" in contact
        assert "url" in contact
        
        # Check license information
        license_info = info["license"]
        assert "name" in license_info
        assert "url" in license_info
        
        # Check description contains important sections
        description = info["description"]
        assert "Authentication" in description
        assert "Rate Limiting" in description
        assert "Error Handling" in description
    
    def test_get_openapi_examples(self):
        """Test OpenAPI examples"""
        examples = get_openapi_examples()
        
        assert isinstance(examples, dict)
        assert "components" in examples
        assert "examples" in examples["components"]
        
        example_names = examples["components"]["examples"].keys()
        assert "SuccessResponse" in example_names
        assert "ErrorResponse" in example_names
        assert "ValidationError" in example_names
        assert "RateLimitError" in example_names
        assert "AuthenticationError" in example_names
        
        # Check example structure
        for example_name, example_data in examples["components"]["examples"].items():
            assert "summary" in example_data
            assert "value" in example_data
            assert isinstance(example_data["summary"], str)
            assert isinstance(example_data["value"], dict)
    
    def test_customize_openapi_schema(self):
        """Test OpenAPI schema customization"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        schema = customize_openapi_schema(app)
        
        assert isinstance(schema, dict)
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        assert "tags" in schema
        assert "servers" in schema
        
        # Check components
        components = schema["components"]
        assert "securitySchemes" in components
        assert "examples" in components
        
        # Check info
        info = schema["info"]
        assert "contact" in info
        assert "license" in info
        assert "termsOfService" in info
        
        # Check external docs
        assert "externalDocs" in schema
        assert "x-logo" in schema
        assert "x-api-status" in schema
    
    def test_setup_openapi_docs_enabled(self):
        """Test OpenAPI docs setup when enabled"""
        app = FastAPI()
        
        with patch('core.openapi.settings') as mock_settings:
            mock_settings.openapi_enabled = True
            mock_settings.docs_url = "/docs"
            mock_settings.redoc_url = "/redoc"
            mock_settings.openapi_url = "/openapi.json"
            
            setup_openapi_docs(app)
            
            client = TestClient(app)
            
            # Test that endpoints are created
            response = client.get("/docs")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            
            response = client.get("/redoc")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            
            response = client.get("/openapi.json")
            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")
    
    def test_setup_openapi_docs_disabled(self):
        """Test OpenAPI docs setup when disabled"""
        app = FastAPI()
        
        with patch('core.openapi.settings') as mock_settings:
            mock_settings.openapi_enabled = False
            
            setup_openapi_docs(app)
            
            client = TestClient(app)
            
            # Test that endpoints are not created
            response = client.get("/docs")
            assert response.status_code == 404
            
            response = client.get("/redoc")
            assert response.status_code == 404
            
            response = client.get("/openapi.json")
            assert response.status_code == 404
    
    def test_configure_openapi_security(self):
        """Test OpenAPI security configuration"""
        app = FastAPI()
        
        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/private")
        async def private_endpoint():
            return {"message": "private"}
        
        configure_openapi_security(app)
        
        schema = app.openapi()
        
        # Check global security requirement
        assert "security" in schema
        assert len(schema["security"]) > 0
        
        # Check security schemes in components
        assert "securitySchemes" in schema["components"]
        assert "BearerAuth" in schema["components"]["securitySchemes"]
        assert "ApiKeyAuth" in schema["components"]["securitySchemes"]
        
        # Check individual path security
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if isinstance(operation, dict):
                    # Public endpoints should not have security
                    if path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
                        assert "security" not in operation
                    else:
                        # Private endpoints should have security
                        assert "security" in operation
    
    def test_add_response_examples(self):
        """Test adding response examples to OpenAPI schema"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        add_response_examples(app)
        
        schema = app.openapi()
        
        # Check that common responses are added
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if isinstance(operation, dict) and "responses" in operation:
                    responses = operation["responses"]
                    
                    # Check common error responses
                    for status_code in ["400", "401", "403", "404", "429", "500"]:
                        if status_code in responses:
                            response = responses[status_code]
                            assert "description" in response
                            assert "content" in response
                            assert "application/json" in response["content"]
                            assert "example" in response["content"]["application/json"]
    
    def test_setup_openapi_configuration_complete(self):
        """Test complete OpenAPI configuration setup"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        setup_openapi_configuration(app)
        
        # Check app configuration
        assert app.title == "MAMS API Gateway"
        assert "MAMS" in app.description
        assert app.version == "1.0.0"
        assert app.contact is not None
        assert app.license_info is not None
        assert app.terms_of_service is not None
        
        # Check OpenAPI schema
        schema = app.openapi()
        assert isinstance(schema, dict)
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
        assert "examples" in schema["components"]
        
        # Test with client
        client = TestClient(app)
        
        # Test API info endpoint
        response = client.get("/api-info")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "version" in data
        assert "documentation" in data
        
        # Test API docs redirect
        response = client.get("/api-docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_openapi_security_environment_specific(self):
        """Test environment-specific OpenAPI security"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Test development environment
        with patch('core.openapi.settings') as mock_settings:
            mock_settings.environment = "development"
            mock_settings.openapi_enabled = True
            mock_settings.docs_url = "/docs"
            mock_settings.redoc_url = "/redoc"
            mock_settings.openapi_url = "/openapi.json"
            
            setup_openapi_docs(app)
            
            client = TestClient(app)
            
            # Documentation should be accessible in development
            response = client.get("/docs")
            assert response.status_code == 200
        
        # Test production environment
        with patch('core.openapi.settings') as mock_settings:
            mock_settings.environment = "production"
            mock_settings.openapi_enabled = True
            mock_settings.docs_url = "/docs"
            mock_settings.redoc_url = "/redoc"
            mock_settings.openapi_url = "/openapi.json"
            
            setup_openapi_docs(app)
            
            client = TestClient(app)
            
            # Documentation should still be accessible (auth handled by middleware)
            response = client.get("/docs")
            assert response.status_code == 200
    
    def test_openapi_servers_environment_specific(self):
        """Test environment-specific server configuration"""
        # Test development environment
        with patch('core.openapi.settings') as mock_settings:
            mock_settings.environment = "development"
            
            servers = get_openapi_servers()
            server_urls = [server["url"] for server in servers]
            assert any("localhost" in url for url in server_urls)
        
        # Test staging environment
        with patch('core.openapi.settings') as mock_settings:
            mock_settings.environment = "staging"
            
            servers = get_openapi_servers()
            server_urls = [server["url"] for server in servers]
            assert any("staging" in url for url in server_urls)
        
        # Test production environment
        with patch('core.openapi.settings') as mock_settings:
            mock_settings.environment = "production"
            
            servers = get_openapi_servers()
            server_urls = [server["url"] for server in servers]
            assert any("api.mams.example.com" in url for url in server_urls)
    
    def test_openapi_json_structure(self):
        """Test OpenAPI JSON structure and content"""
        app = FastAPI()
        
        @app.get("/test", tags=["test"])
        async def test_endpoint():
            """Test endpoint with documentation"""
            return {"message": "test"}
        
        setup_openapi_configuration(app)
        
        client = TestClient(app)
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Check OpenAPI version
        assert "openapi" in schema
        assert schema["openapi"].startswith("3.")
        
        # Check required sections
        required_sections = ["info", "paths", "components", "tags", "servers"]
        for section in required_sections:
            assert section in schema
        
        # Check info section
        info = schema["info"]
        assert "title" in info
        assert "description" in info
        assert "version" in info
        assert "contact" in info
        assert "license" in info
        
        # Check components
        components = schema["components"]
        assert "securitySchemes" in components
        assert "examples" in components
        
        # Check paths
        paths = schema["paths"]
        assert "/test" in paths
        
        # Check tags
        tags = schema["tags"]
        assert isinstance(tags, list)
        assert len(tags) > 0


class TestOpenAPIIntegration:
    """Integration tests for OpenAPI configuration"""
    
    def test_full_openapi_integration(self):
        """Test complete OpenAPI integration"""
        app = FastAPI()
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        @app.get("/api/v1/test", tags=["test"])
        async def test_endpoint():
            return {"message": "test"}
        
        setup_openapi_configuration(app)
        
        client = TestClient(app)
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        
        # Verify schema structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "redoc" in response.text.lower()
        
        # Test API info
        response = client.get("/api-info")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "documentation" in data
        
        # Test API docs redirect
        response = client.get("/api-docs")
        assert response.status_code == 200
        assert "refresh" in response.text.lower()
    
    def test_openapi_with_authentication(self):
        """Test OpenAPI with authentication requirements"""
        app = FastAPI()
        
        @app.get("/public")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/private")
        async def private_endpoint():
            return {"message": "private"}
        
        setup_openapi_configuration(app)
        
        client = TestClient(app)
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check security schemes
        assert "securitySchemes" in schema["components"]
        security_schemes = schema["components"]["securitySchemes"]
        assert "BearerAuth" in security_schemes
        assert "ApiKeyAuth" in security_schemes
        
        # Check global security
        assert "security" in schema
        
        # Check path-specific security
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if isinstance(operation, dict):
                    # Public endpoints should not have security
                    if path in ["/health", "/public"]:
                        continue
                    # Private endpoints should have security
                    assert "security" in operation
    
    def test_openapi_examples_in_responses(self):
        """Test OpenAPI examples in response documentation"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        setup_openapi_configuration(app)
        
        client = TestClient(app)
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check that examples are present in components
        assert "examples" in schema["components"]
        examples = schema["components"]["examples"]
        
        # Check specific examples
        assert "SuccessResponse" in examples
        assert "ErrorResponse" in examples
        assert "ValidationError" in examples
        
        # Check example structure
        for example_name, example_data in examples.items():
            assert "summary" in example_data
            assert "value" in example_data
            assert isinstance(example_data["value"], dict)
    
    def test_openapi_tags_and_descriptions(self):
        """Test OpenAPI tags and descriptions"""
        app = FastAPI()
        
        @app.get("/health", tags=["health"])
        async def health_check():
            return {"status": "healthy"}
        
        @app.get("/api/v1/users", tags=["users"])
        async def get_users():
            return {"users": []}
        
        setup_openapi_configuration(app)
        
        client = TestClient(app)
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check tags
        assert "tags" in schema
        tags = schema["tags"]
        assert isinstance(tags, list)
        
        # Check specific tags
        tag_names = [tag["name"] for tag in tags]
        assert "health" in tag_names
        assert "users" in tag_names
        
        # Check tag descriptions
        for tag in tags:
            assert "name" in tag
            assert "description" in tag
            assert len(tag["description"]) > 0