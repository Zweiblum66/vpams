# Blockchain Integration for Rights Management

## Overview

The Rights Management Service now includes comprehensive blockchain storage capabilities for immutable rights tracking, smart contract integration, and decentralized storage via IPFS.

## Features

### 1. Multi-Blockchain Support
- **Ethereum**: Full support for mainnet and testnet deployments
- **Hyperledger**: Enterprise blockchain integration (planned)
- **IPFS**: Decentralized storage for large rights documents
- **Private Blockchain**: Built-in private blockchain for testing and private deployments

### 2. Rights Record Storage
- Immutable storage of licenses, usage records, and rights transfers
- Hash-linked records for complete audit trail
- Cryptographic verification of record integrity
- Support for on-chain and off-chain (IPFS) storage

### 3. Smart Contract Integration
- Deploy and interact with rights management smart contracts
- Pre-built contract types:
  - License contracts
  - Royalty distribution contracts
  - Usage tracking contracts
  - Rights transfer contracts
  - Escrow contracts

### 4. Security Features
- End-to-end encryption for sensitive data
- Multi-signature support for critical operations
- AES-GCM authenticated encryption
- Secure key management

## API Endpoints

### Configuration Management

#### Create Blockchain Configuration
```http
POST /api/v1/blockchain/config
Authorization: Bearer {token}

{
  "blockchain_type": "ethereum",
  "network": "testnet",
  "node_url": "https://ropsten.infura.io/v3/YOUR-PROJECT-ID",
  "chain_id": 3,
  "encryption_enabled": true,
  "multi_sig_required": false,
  "batch_size": 100,
  "confirmation_blocks": 6
}
```

### Rights Storage

#### Store Rights on Blockchain
```http
POST /api/v1/blockchain/rights?config_id={config_id}
Authorization: Bearer {token}

{
  "record_type": "license_creation",
  "entity_id": "license-123",
  "entity_type": "license",
  "rights_data": {
    "license_number": "LIC-2024-001",
    "rights_type": "broadcast",
    "territories": ["US", "CA"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  },
  "parties": [
    {
      "id": "party-001",
      "role": "licensor",
      "name": "Content Owner Inc"
    },
    {
      "id": "party-002",
      "role": "licensee",
      "name": "Broadcasting Corp"
    }
  ],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

#### Verify Rights Record
```http
GET /api/v1/blockchain/rights/verify?entity_type=license&entity_id=license-123
Authorization: Bearer {token}
```

Response:
```json
{
  "is_valid": true,
  "record_hash": "0x7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730",
  "blockchain_hash": "0x123...",
  "transaction_id": "0xabc...",
  "block_number": 12345678,
  "timestamp": "2024-01-15T10:30:00Z",
  "verification_details": {
    "confirmations": 12,
    "status": "confirmed"
  }
}
```

### Smart Contracts

#### Deploy Smart Contract
```http
POST /api/v1/blockchain/contracts
Authorization: Bearer {token}

{
  "contract_type": "license",
  "contract_name": "BroadcastLicenseContract",
  "description": "Smart contract for broadcast licensing",
  "abi": {...},
  "bytecode": "0x608060405234801561001057600080fd5b50...",
  "deploy_immediately": true,
  "constructor_params": {
    "owner": "0x1234567890abcdef1234567890abcdef12345678"
  }
}
```

#### Interact with Contract
```http
POST /api/v1/blockchain/contracts/{contract_id}/interact
Authorization: Bearer {token}

{
  "method_name": "createLicense",
  "parameters": {
    "licenseId": "license-456",
    "expiryDate": 1735689600,
    "royaltyPercentage": 15
  },
  "from_address": "0x1234567890abcdef1234567890abcdef12345678",
  "gas_limit": 100000
}
```

### IPFS Storage

#### Upload to IPFS
```http
POST /api/v1/blockchain/ipfs/upload
Authorization: Bearer {token}

{
  "data": {
    "license_document": "base64_encoded_pdf_content",
    "metadata": {
      "title": "Broadcast License Agreement",
      "parties": ["Content Owner", "Broadcaster"],
      "created_date": "2024-01-15"
    }
  },
  "pin": true,
  "encrypt": true
}
```

Response:
```json
{
  "ipfs_hash": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
  "size": 15420,
  "gateway_url": "https://ipfs.io/ipfs/QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
  "pinned": true,
  "encrypted": true,
  "encryption_key": "key_id_123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Statistics

#### Get Blockchain Statistics
```http
GET /api/v1/blockchain/stats?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

## Usage Examples

### 1. Setting Up Ethereum Integration

```python
# Configure Ethereum connection
config = {
    "blockchain_type": "ethereum",
    "network": "mainnet",
    "node_url": "https://mainnet.infura.io/v3/YOUR-PROJECT-ID",
    "chain_id": 1,
    "contract_address": "0x...",  # Your deployed contract
    "encryption_enabled": True,
    "confirmation_blocks": 12
}

# Create configuration
response = await client.post("/api/v1/blockchain/config", json=config)
config_id = response.json()["id"]
```

### 2. Storing License on Blockchain

```python
# Prepare license data
license_record = {
    "record_type": "license_creation",
    "entity_id": "license-789",
    "entity_type": "license",
    "rights_data": {
        "license_number": "LIC-2024-789",
        "type": "streaming",
        "territories": ["WORLDWIDE"],
        "duration": "perpetual"
    },
    "parties": [
        {"id": "p1", "role": "owner", "name": "Studio XYZ"},
        {"id": "p2", "role": "distributor", "name": "Stream Platform"}
    ]
}

# Store on blockchain
response = await client.post(
    f"/api/v1/blockchain/rights?config_id={config_id}",
    json=license_record
)
```

### 3. Verifying Rights Chain

```python
# Verify entire rights chain for an asset
verification = await client.get(
    "/api/v1/blockchain/rights/verify",
    params={"entity_type": "license", "entity_id": "license-789"}
)

if verification.json()["is_valid"]:
    print("Rights record verified on blockchain")
    print(f"Transaction: {verification.json()['transaction_id']}")
    print(f"Block: {verification.json()['block_number']}")
```

## Private Blockchain Mode

For development and testing, the service includes a built-in private blockchain:

1. **Create Private Config**:
```json
{
  "blockchain_type": "private",
  "network": "local",
  "store_full_data": true,
  "confirmation_blocks": 1
}
```

2. **Mine Blocks**:
```python
# Create a new block
block_data = {
    "data": {
        "transactions": ["tx1", "tx2"],
        "metadata": {"miner": "node1"}
    }
}

response = await client.post(
    f"/api/v1/blockchain/blocks?config_id={config_id}",
    json=block_data
)
```

## Security Considerations

1. **Key Management**
   - Private keys should never be stored in the database
   - Use hardware security modules (HSM) for production
   - Implement key rotation policies

2. **Data Encryption**
   - All sensitive data is encrypted before blockchain storage
   - Encryption keys are managed separately from blockchain data
   - Support for both symmetric (AES) and asymmetric encryption

3. **Access Control**
   - Admin permissions required for configuration changes
   - User-level permissions for transaction creation
   - Read-only access for verification endpoints

4. **Multi-Signature Transactions**
   - Configure minimum signatures for critical operations
   - Support for threshold signatures (e.g., 2-of-3)
   - Automatic notification of pending signatures

## Performance Optimization

1. **Batch Processing**
   - Group multiple transactions for efficiency
   - Configurable batch sizes
   - Automatic retry for failed transactions

2. **IPFS Integration**
   - Store large documents off-chain
   - Only store hashes on blockchain
   - Automatic pinning for data availability

3. **Caching**
   - Cache verified records
   - Cache contract ABI and metadata
   - Configurable cache TTL

## Monitoring and Alerts

1. **Transaction Monitoring**
   - Track pending transactions
   - Alert on failed transactions
   - Monitor gas costs (Ethereum)

2. **Chain Health**
   - Monitor node connectivity
   - Track block confirmation times
   - Alert on chain reorganizations

3. **Audit Logging**
   - All blockchain operations are logged
   - Separate audit trail for compliance
   - Integration with main audit system

## Future Enhancements

1. **Cross-Chain Support**
   - Bridge between different blockchains
   - Atomic swaps for rights transfers
   - Multi-chain verification

2. **Advanced Smart Contracts**
   - Automated royalty distribution
   - Time-locked rights releases
   - Conditional licensing terms

3. **Decentralized Identity**
   - DID integration for party verification
   - Self-sovereign identity support
   - Zero-knowledge proofs for privacy

## Troubleshooting

### Common Issues

1. **Transaction Pending Too Long**
   - Check gas price (Ethereum)
   - Verify node connectivity
   - Check network congestion

2. **Verification Failures**
   - Ensure record exists on chain
   - Check for chain reorganization
   - Verify hash calculation

3. **IPFS Connection Issues**
   - Check IPFS daemon status
   - Verify firewall rules
   - Test gateway connectivity

### Debug Endpoints

```http
# Check blockchain health
GET /api/v1/blockchain/health

# Get pending transactions
GET /api/v1/blockchain/transactions?status=pending

# Retry failed transaction
POST /api/v1/blockchain/transactions/{tx_id}/retry
```

## Conclusion

The blockchain integration provides a robust, secure, and verifiable system for rights management. By combining on-chain transactions with off-chain storage and smart contracts, the system offers flexibility, scalability, and immutability for critical rights data.