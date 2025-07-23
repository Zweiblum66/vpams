"""Tests for Web3 Integration Service"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from src.main import app

client = TestClient(app)

class TestWeb3Integration:
    """Test Web3 integration endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "web3-integration"
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "python_info" in response.text
    
    @patch('src.services.web3_connector.Web3ConnectorService')
    def test_connect_wallet_validation(self, mock_connector):
        """Test wallet connection with invalid address"""
        mock_instance = mock_connector.return_value
        mock_instance.is_valid_address.return_value = False
        
        response = client.post(
            "/api/v1/auth/connect-wallet",
            params={
                "address": "invalid_address",
                "wallet_type": "metamask",
                "chain_type": "ethereum",
                "user_id": "test_user"
            }
        )
        assert response.status_code == 400
        assert "Invalid wallet address" in response.json()["detail"]

class TestENSRoutes:
    """Test ENS-related endpoints"""
    
    @patch('src.services.web3_connector.Web3ConnectorService')
    def test_resolve_ens_invalid_format(self, mock_connector):
        """Test ENS resolution with invalid format"""
        response = client.get("/api/v1/ens/resolve/invalid_name")
        assert response.status_code == 400
        assert "Invalid ENS name format" in response.json()["detail"]
    
    @patch('src.services.web3_connector.Web3ConnectorService')
    def test_resolve_ens_not_found(self, mock_connector):
        """Test ENS resolution for non-existent name"""
        mock_instance = mock_connector.return_value
        mock_instance.get_address_from_ens = AsyncMock(return_value=None)
        
        response = client.get("/api/v1/ens/resolve/nonexistent.eth")
        assert response.status_code == 404
        assert "ENS name not found" in response.json()["detail"]

class TestTokenGateRoutes:
    """Test token-gating endpoints"""
    
    def test_create_token_gate_rule_validation(self):
        """Test token gate rule creation with missing data"""
        response = client.post(
            "/api/v1/token-gate/rules",
            json={}  # Empty payload should fail validation
        )
        assert response.status_code == 422  # Validation error

class TestStorageRoutes:
    """Test decentralized storage endpoints"""
    
    @patch('src.services.ipfs_service.IPFSService')
    def test_ipfs_upload_without_file(self, mock_ipfs):
        """Test IPFS upload without file"""
        response = client.post("/api/v1/storage/ipfs/upload")
        assert response.status_code == 422  # Missing file in multipart form

@pytest.mark.asyncio
class TestAsyncServices:
    """Test async service methods"""
    
    @patch('web3.Web3')
    async def test_web3_connector_initialization(self, mock_web3):
        """Test Web3 connector service initialization"""
        from src.services.web3_connector import Web3ConnectorService
        
        # Mock Web3 instance
        mock_web3_instance = Mock()
        mock_web3.return_value = mock_web3_instance
        mock_web3_instance.isConnected.return_value = True
        
        connector = Web3ConnectorService()
        assert connector is not None
    
    async def test_ipfs_service_initialization(self):
        """Test IPFS service initialization"""
        from src.services.ipfs_service import IPFSService
        
        ipfs_service = IPFSService()
        assert ipfs_service is not None
        assert ipfs_service.api_url == "http://localhost:5001"
    
    async def test_did_service_create_ethr_did(self):
        """Test DID service Ethereum DID creation"""
        from src.services.did_service import DIDService
        
        did_service = DIDService()
        test_address = "0x742d35Cc6634C0532925a3b8D7389d5f6b5f3f9e"
        test_public_key = "0x04abcd1234..."
        
        did_document = await did_service.create_ethr_did(
            address=test_address,
            public_key=test_public_key
        )
        
        assert did_document["id"] == f"did:ethr:{test_address}"
        assert "verificationMethod" in did_document
        assert "authentication" in did_document

class TestConfiguration:
    """Test configuration and environment variables"""
    
    def test_config_loading(self):
        """Test that configuration loads properly"""
        from src.core.config import settings
        
        assert settings.SERVICE_NAME == "web3-integration"
        assert settings.SERVICE_PORT == 8021
        assert hasattr(settings, 'ETHEREUM_RPC_URL')
        assert hasattr(settings, 'IPFS_API_URL')
    
    def test_chain_configurations(self):
        """Test that chain configurations are available"""
        from src.core.config import settings
        
        # These should be configurable
        chains = [
            'ETHEREUM_RPC_URL',
            'POLYGON_RPC_URL', 
            'ARBITRUM_RPC_URL',
            'OPTIMISM_RPC_URL',
            'AVALANCHE_RPC_URL',
            'BSC_RPC_URL'
        ]
        
        for chain in chains:
            assert hasattr(settings, chain)

# Fixtures for testing
@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session

@pytest.fixture  
def mock_web3_user():
    """Mock Web3 user model"""
    from src.models.web3_models import Web3User
    
    user = Mock(spec=Web3User)
    user.id = "test_user_id"
    user.user_id = "mams_user_123"
    user.primary_address = "0x742d35Cc6634C0532925a3b8D7389d5f6b5f3f9e"
    user.wallets = []
    return user

@pytest.fixture
def sample_token_gate_rule():
    """Sample token gate rule for testing"""
    return {
        "name": "NFT Holder Access",
        "resource_type": "asset",
        "resource_id": "asset_123",
        "chain_type": "ethereum",
        "requirements": {
            "nft_collections": [
                {
                    "name": "Bored Ape Yacht Club",
                    "address": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
                    "min_quantity": 1
                }
            ]
        },
        "is_active": True,
        "created_by": "admin_user"
    }