# MAMS Blockchain Service

Distributed Ledger Technology (DLT) service for media rights management using blockchain technology and IPFS for decentralized content storage.

## Features

### Core Blockchain Features
- **Media Rights NFTs**: Mint and manage media rights as non-fungible tokens
- **Multi-Chain Support**: Ethereum, Polygon, Avalanche, and Binance Smart Chain
- **License Management**: Create, manage, and enforce media licenses
- **Royalty Payments**: Automated royalty distribution system
- **Rights Verification**: Blockchain-based ownership verification
- **Transfer Management**: Secure rights ownership transfers

### IPFS Integration
- **Decentralized Storage**: Store metadata and content on IPFS
- **Content Addressing**: Immutable content hashes for integrity
- **Pin Management**: Control content persistence and availability
- **Gateway Access**: HTTP gateway for easy content access

### Smart Contract Features
- **ERC-721 Compatible**: Standard NFT functionality
- **License Creation**: On-chain license agreements
- **Usage Tracking**: Monitor license usage and compliance
- **Royalty Distribution**: Automated payment splits
- **Access Control**: Role-based permissions and restrictions

## Architecture

### Services
- **BlockchainService**: Core blockchain operations and smart contract interaction
- **IPFSService**: Decentralized content storage and retrieval
- **DatabaseService**: Local data persistence and caching

### Smart Contracts
- **MediaRights.sol**: Main contract for rights management
- **License Management**: On-chain licensing system
- **Royalty Distribution**: Automated payment handling

### Supported Networks
- **Ethereum Mainnet/Goerli**: Primary network for high-value assets
- **Polygon**: Low-cost transactions for frequent operations
- **Avalanche**: Fast finality for time-sensitive transactions
- **Binance Smart Chain**: Alternative low-cost option

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- IPFS Node
- Blockchain RPC Access

### Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd services/blockchain

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Environment Variables
```env
# Service Configuration
DEBUG=true
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/blockchain_db
REDIS_URL=redis://localhost:6379/0

# Blockchain Networks
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID
POLYGON_RPC_URL=https://polygon-rpc.com
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
BSC_RPC_URL=https://bsc-dataseed.binance.org

# Private Key (for transaction signing)
BLOCKCHAIN_PRIVATE_KEY=0x...

# Smart Contract Addresses
RIGHTS_CONTRACT_ETHEREUM=0x...
RIGHTS_CONTRACT_POLYGON=0x...
RIGHTS_CONTRACT_AVALANCHE=0x...
RIGHTS_CONTRACT_BSC=0x...

# IPFS Configuration
IPFS_NODE_URL=http://localhost:5001
IPFS_GATEWAY_URL=http://localhost:8080

# Security
JWT_SECRET=your-jwt-secret-here
```

## Docker Deployment

### Development Environment
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f blockchain-service

# Stop services
docker-compose down
```

### Services Included
- **blockchain-service**: Main application
- **postgres**: Database for blockchain data
- **redis**: Caching and rate limiting
- **ipfs**: IPFS node for content storage
- **ganache**: Local blockchain for development

## API Endpoints

### Asset Rights Management
```
POST   /api/v1/assets/rights              # Create asset rights
GET    /api/v1/assets/{id}/rights         # Get asset rights
POST   /api/v1/assets/rights/transfer     # Transfer rights ownership
```

### License Management
```
POST   /api/v1/licenses                   # Create license
GET    /api/v1/licenses/{id}              # Get license details
PUT    /api/v1/licenses/{id}              # Update license
DELETE /api/v1/licenses/{id}              # Revoke license
```

### Royalty Payments
```
POST   /api/v1/royalties/payment          # Create royalty payment
GET    /api/v1/royalties/calculate        # Calculate royalty amount
GET    /api/v1/royalties/history          # Payment history
```

### IPFS Operations
```
POST   /api/v1/ipfs/upload                # Upload content to IPFS
GET    /api/v1/ipfs/{hash}                # Get IPFS content info
POST   /api/v1/ipfs/pin                   # Pin content
DELETE /api/v1/ipfs/pin/{hash}            # Unpin content
```

### Blockchain Utilities
```
GET    /api/v1/networks/stats             # Network statistics
GET    /api/v1/addresses/{addr}/balance   # Address balance
GET    /api/v1/transactions/{hash}        # Transaction status
POST   /api/v1/verify/ownership           # Verify ownership
```

## Usage Examples

### Create Asset Rights
```python
import requests

# Prepare asset data
data = {
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "owner_address": "0x742d35cc6ea7c6c3a1b7c1c9e2a8ff8a8a8b8c8d",
    "creator_address": "0x742d35cc6ea7c6c3a1b7c1c9e2a8ff8a8a8b8c8d",
    "rights_type": "ownership",
    "title": "My Media Asset",
    "description": "High-quality video content",
    "royalty_percentage": 5.0,
    "network": "polygon"
}

# Create rights
response = requests.post("http://localhost:8012/api/v1/assets/rights", json=data)
rights_info = response.json()
print(f"Rights created: {rights_info['transaction_hash']}")
```

### Create License
```python
# License data
license_data = {
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "licensee_address": "0x123456789abcdef123456789abcdef1234567890",
    "rights_type": "usage",
    "license_fee": "0.1",  # ETH
    "valid_from": "2024-01-01T00:00:00Z",
    "valid_until": "2024-12-31T23:59:59Z",
    "max_uses": 100,
    "terms": {
        "commercial_use": True,
        "territory": ["US", "EU"],
        "media_types": ["digital", "broadcast"]
    }
}

# Create license
response = requests.post("http://localhost:8012/api/v1/licenses", json=license_data)
license_info = response.json()
print(f"License created: {license_info['license_number']}")
```

### Upload to IPFS
```python
# Upload file
files = {"file": open("media_file.mp4", "rb")}
data = {"content_type": "video", "pin": True}

response = requests.post(
    "http://localhost:8012/api/v1/ipfs/upload",
    files=files,
    data=data
)
ipfs_info = response.json()
print(f"IPFS hash: {ipfs_info['ipfs_hash']}")
print(f"Gateway URL: {ipfs_info['gateway_url']}")
```

## Smart Contract Deployment

### Deploy Rights Contract
```bash
# Install Hardhat
npm install --save-dev hardhat

# Compile contracts
npx hardhat compile

# Deploy to network
npx hardhat run scripts/deploy.js --network polygon

# Verify contract
npx hardhat verify --network polygon CONTRACT_ADDRESS
```

### Contract Configuration
```javascript
// hardhat.config.js
module.exports = {
  solidity: "0.8.19",
  networks: {
    polygon: {
      url: "https://polygon-rpc.com",
      accounts: [PRIVATE_KEY]
    }
  }
};
```

## Database Schema

### Key Tables
- **blockchain_assets**: NFT representations of media assets
- **media_rights**: Rights information and terms
- **rights_licenses**: License agreements and usage tracking
- **blockchain_transactions**: Transaction history and status
- **royalty_payments**: Payment records and analytics
- **ipfs_hashes**: IPFS content mapping and metadata

### Relationships
- Assets → Rights (1:N)
- Assets → Licenses (1:N)
- Licenses → Payments (1:N)
- Assets → Transactions (1:N)

## Monitoring and Logging

### Health Checks
```bash
# Service health
curl http://localhost:8012/health

# Network status
curl http://localhost:8012/api/v1/networks/stats

# IPFS status
curl http://localhost:8012/api/v1/ipfs/node/info
```

### Metrics
- Transaction success rates
- Network gas costs
- IPFS pin counts
- License creation rates
- Royalty payment volumes

## Security Considerations

### Private Key Management
- Use hardware security modules (HSM) in production
- Implement key rotation policies
- Separate keys for different networks
- Use multi-signature wallets for high-value operations

### Smart Contract Security
- Code audits before deployment
- Formal verification for critical functions
- Gradual rollout with usage limits
- Emergency pause mechanisms

### API Security
- Rate limiting per API key
- Input validation and sanitization
- HTTPS only in production
- JWT token authentication

## Development

### Running Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Contract tests
npx hardhat test
```

### Code Quality
```bash
# Linting
ruff check src/
black src/

# Type checking
mypy src/

# Security scanning
bandit -r src/
```

## Troubleshooting

### Common Issues

#### Connection Errors
```
Error: Failed to connect to blockchain network
Solution: Check RPC URL and network connectivity
```

#### Transaction Failures
```
Error: Transaction failed with gas limit exceeded
Solution: Increase gas limit or optimize contract calls
```

#### IPFS Upload Issues
```
Error: IPFS node not responding
Solution: Check IPFS daemon status and API port
```

### Debugging Tools
- **Web3 Console**: Interactive blockchain debugging
- **IPFS Desktop**: GUI for IPFS operations
- **Etherscan**: Transaction and contract verification
- **Polygon Explorer**: Network-specific debugging

## Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

### Code Standards
- Follow PEP 8 for Python code
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain test coverage > 90%

### Smart Contract Standards
- Follow Solidity style guide
- Use OpenZeppelin contracts
- Implement comprehensive tests
- Document all public functions

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:
- GitHub Issues: [Create Issue](https://github.com/mams/blockchain-service/issues)
- Documentation: [Wiki](https://github.com/mams/blockchain-service/wiki)
- Discord: [MAMS Community](https://discord.gg/mams)