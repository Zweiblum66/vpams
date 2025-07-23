"""
Test suite for MAMS Python SDK
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import httpx
from mams import MAMSClient, AsyncMAMSClient
from mams.auth import APIKeyAuth, JWTAuth, OAuth2Provider
from mams.exceptions import AuthenticationError, NotFoundError, ValidationError
from mams.config import Config


class TestSDKConfiguration:
    """Test SDK configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = Config()
        assert config.base_url == "https://api.mams.io"
        assert config.api_version == "v1"
        assert config.timeout == 30.0
        assert config.max_retries == 3
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = Config(
            base_url="https://custom.mams.io",
            timeout=60.0,
            max_retries=5
        )
        assert config.base_url == "https://custom.mams.io"
        assert config.timeout == 60.0
        assert config.max_retries == 5
    
    def test_api_url_generation(self):
        """Test API URL generation"""
        config = Config()
        assert config.get_api_url("assets") == "https://api.mams.io/api/v1/assets"
        assert config.get_api_url("/assets") == "https://api.mams.io/api/v1/assets"


class TestAuthentication:
    """Test authentication providers"""
    
    def test_api_key_auth(self):
        """Test API key authentication"""
        auth = APIKeyAuth("test-api-key")
        headers = auth.get_headers()
        assert headers["X-API-Key"] == "test-api-key"
        assert auth.refresh_token() is True
    
    def test_jwt_auth(self):
        """Test JWT authentication"""
        # Valid JWT token (mock)
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjk5OTk5OTk5OTl9.invalid"
        auth = JWTAuth(token)
        headers = auth.get_headers()
        assert headers["Authorization"] == f"Bearer {token}"
    
    def test_oauth2_provider(self):
        """Test OAuth2 provider"""
        provider = OAuth2Provider(
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback"
        )
        
        auth_url = provider.get_authorization_url()
        assert "client_id=test-client" in auth_url
        assert "redirect_uri=http%3A//localhost%3A8000/callback" in auth_url


class TestMAMSClient:
    """Test MAMS client"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return MAMSClient(
            auth=APIKeyAuth("test-key"),
            base_url="http://localhost:8000"
        )
    
    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response"""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.json.return_value = {"data": {"id": "123", "name": "test"}}
        return response
    
    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.config.base_url == "http://localhost:8000"
        assert isinstance(client.auth, APIKeyAuth)
        assert hasattr(client, "assets")
        assert hasattr(client, "projects")
        assert hasattr(client, "workflows")
    
    @patch("httpx.request")
    def test_request_with_auth(self, mock_request, client, mock_response):
        """Test authenticated request"""
        mock_request.return_value = mock_response
        
        result = client.request("GET", "assets")
        
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["headers"]["X-API-Key"] == "test-key"
        assert result == {"data": {"id": "123", "name": "test"}}
    
    @patch("httpx.request")
    def test_error_handling(self, mock_request, client):
        """Test error handling"""
        error_response = Mock(spec=httpx.Response)
        error_response.status_code = 404
        error_response.json.return_value = {"message": "Not found"}
        mock_request.return_value = error_response
        
        with pytest.raises(NotFoundError):
            client.request("GET", "assets/invalid-id")


class TestAssetsResource:
    """Test assets resource"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return MAMSClient(
            auth=APIKeyAuth("test-key"),
            base_url="http://localhost:8000"
        )
    
    @patch("httpx.request")
    def test_list_assets(self, mock_request, client):
        """Test listing assets"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "1", "name": "asset1.mp4", "type": "video"},
                {"id": "2", "name": "asset2.jpg", "type": "image"}
            ]
        }
        mock_request.return_value = mock_response
        
        assets = client.assets.list(limit=10)
        
        assert len(assets) == 2
        assert assets[0].name == "asset1.mp4"
        assert assets[1].type == "image"
    
    @patch("httpx.request")
    def test_get_asset(self, mock_request, client):
        """Test getting single asset"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "id": "123",
                "name": "test.mp4",
                "type": "video",
                "size_bytes": 1024000,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
        mock_request.return_value = mock_response
        
        asset = client.assets.get("123")
        
        assert asset.id == "123"
        assert asset.name == "test.mp4"
        assert asset.type == "video"
    
    @patch("httpx.request")
    def test_upload_asset(self, mock_request, client):
        """Test uploading asset"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "id": "new-123",
                "name": "upload.mp4",
                "type": "video",
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
        mock_request.return_value = mock_response
        
        with patch("builtins.open", mock_open(read_data=b"fake video data")):
            mock_file = Mock()
            mock_file.read.return_value = b"fake video data"
            
            asset = client.assets.upload(
                file=mock_file,
                name="upload.mp4",
                type="video"
            )
        
        assert asset.id == "new-123"
        assert asset.name == "upload.mp4"
    
    def test_detect_asset_type(self, client):
        """Test asset type detection"""
        assert client.assets._detect_asset_type(".mp4") == "video"
        assert client.assets._detect_asset_type(".jpg") == "image"
        assert client.assets._detect_asset_type(".mp3") == "audio"
        assert client.assets._detect_asset_type(".pdf") == "document"


class TestProjectsResource:
    """Test projects resource"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return MAMSClient(
            auth=APIKeyAuth("test-key"),
            base_url="http://localhost:8000"
        )
    
    @patch("httpx.request")
    def test_create_project(self, mock_request, client):
        """Test creating project"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "id": "proj-123",
                "name": "Test Project",
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "owner_id": "user-123"
            }
        }
        mock_request.return_value = mock_response
        
        project = client.projects.create(
            name="Test Project",
            description="A test project"
        )
        
        assert project.id == "proj-123"
        assert project.name == "Test Project"
    
    @patch("httpx.request")
    def test_add_asset_to_project(self, mock_request, client):
        """Test adding asset to project"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "asset_id": "asset-123",
                "project_id": "proj-123",
                "added_at": "2024-01-01T00:00:00Z"
            }
        }
        mock_request.return_value = mock_response
        
        result = client.projects.add_asset("proj-123", "asset-123")
        
        assert result["asset_id"] == "asset-123"
        assert result["project_id"] == "proj-123"


class TestWorkflowsResource:
    """Test workflows resource"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return MAMSClient(
            auth=APIKeyAuth("test-key"),
            base_url="http://localhost:8000"
        )
    
    @patch("httpx.request")
    def test_start_workflow(self, mock_request, client):
        """Test starting workflow"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "id": "exec-123",
                "workflow_id": "wf-123",
                "status": "running",
                "started_at": "2024-01-01T00:00:00Z"
            }
        }
        mock_request.return_value = mock_response
        
        execution = client.workflows.start_workflow(
            "wf-123",
            context={"asset_id": "asset-123"}
        )
        
        assert execution["id"] == "exec-123"
        assert execution["status"] == "running"
    
    @patch("httpx.request")
    def test_approve_step(self, mock_request, client):
        """Test approving workflow step"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = client.workflows.approve_step(
            "exec-123",
            "step-456",
            comment="Approved by test"
        )
        
        assert result is True


@pytest.mark.asyncio
class TestAsyncMAMSClient:
    """Test async MAMS client"""
    
    @pytest.fixture
    def client(self):
        """Create test async client"""
        return AsyncMAMSClient(
            auth=APIKeyAuth("test-key"),
            base_url="http://localhost:8000"
        )
    
    @patch("httpx.AsyncClient.request")
    async def test_async_request(self, mock_request, client):
        """Test async request"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": "123"}}
        mock_request.return_value = mock_response
        
        result = await client.request("GET", "assets")
        
        assert result == {"data": {"id": "123"}}
    
    @patch("httpx.AsyncClient.request")
    async def test_async_list_assets(self, mock_request, client):
        """Test async asset listing"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "1", "name": "test.mp4", "type": "video"}]
        }
        mock_request.return_value = mock_response
        
        assets = await client.assets.list()
        
        assert len(assets) == 1
        assert assets[0].name == "test.mp4"


class TestErrorHandling:
    """Test error handling"""
    
    def test_authentication_error(self):
        """Test authentication error handling"""
        response = Mock(spec=httpx.Response)
        response.status_code = 401
        response.json.return_value = {"message": "Invalid API key"}
        
        from mams.exceptions import handle_error_response
        
        with pytest.raises(AuthenticationError) as exc_info:
            handle_error_response(response)
        
        assert "Invalid API key" in str(exc_info.value)
    
    def test_validation_error(self):
        """Test validation error handling"""
        response = Mock(spec=httpx.Response)
        response.status_code = 422
        response.json.return_value = {
            "message": "Validation failed",
            "details": {"errors": {"name": ["This field is required"]}}
        }
        
        from mams.exceptions import handle_error_response
        
        with pytest.raises(ValidationError) as exc_info:
            handle_error_response(response)
        
        assert exc_info.value.errors["name"] == ["This field is required"]


if __name__ == "__main__":
    pytest.main([__file__])