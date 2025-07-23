# MAMS Quantum Encryption Service

A comprehensive post-quantum cryptography service for the MAMS platform, providing quantum-resistant encryption, digital signatures, and key management capabilities.

## Overview

The Quantum Encryption Service implements state-of-the-art post-quantum cryptographic algorithms to protect data against both classical and quantum computing threats. It supports multiple NIST-approved quantum-resistant algorithms and provides hybrid encryption modes for transitional security.

## Features

### Core Capabilities
- **Quantum-Resistant Key Generation**: Support for multiple PQC algorithms
- **Hybrid Encryption**: Combine classical and quantum-resistant algorithms
- **Digital Signatures**: Quantum-safe signing and verification
- **Key Management**: Automated rotation, expiration, and lifecycle management
- **Batch Operations**: Process multiple encryption/decryption requests efficiently
- **Security Analytics**: Real-time metrics and security assessments

### Supported Algorithms

#### Key Encapsulation Mechanisms (KEMs)
- **CRYSTALS-Kyber**: 512, 768, 1024 (NIST selected)
- **NTRU**: HPS2048509, HPS2048677, HPS4096821
- **SABER**: Light, Standard, Fire

#### Digital Signatures
- **CRYSTALS-Dilithium**: 2, 3, 5 (NIST selected)
- **FALCON**: 512, 1024 (NIST selected)
- **SPHINCS+**: SHA256-128f, SHA256-192f, SHA256-256f (NIST selected)

#### Classical Algorithms (for hybrid mode)
- **RSA**: 2048, 4096
- **ECC**: P-256, P-384, P-521
- **AES**: 256-bit

## API Endpoints

### Key Management
- `POST /api/v1/quantum/keys` - Create quantum key pair
- `GET /api/v1/quantum/keys` - List keys
- `GET /api/v1/quantum/keys/{key_id}` - Get specific key
- `PATCH /api/v1/quantum/keys/{key_id}` - Update key
- `DELETE /api/v1/quantum/keys/{key_id}/revoke` - Revoke key
- `POST /api/v1/quantum/keys/{key_id}/rotate` - Rotate key

### Cryptographic Operations
- `POST /api/v1/quantum/keys/encrypt` - Encrypt data
- `POST /api/v1/quantum/keys/decrypt` - Decrypt data
- `POST /api/v1/quantum/keys/sign` - Sign data
- `POST /api/v1/quantum/keys/verify` - Verify signature
- `POST /api/v1/quantum/keys/batch/encrypt` - Batch encryption

### Analytics & Monitoring
- `GET /api/v1/quantum/analytics/metrics` - Get metrics
- `GET /api/v1/quantum/analytics/security/assessment` - Security assessment
- `GET /api/v1/quantum/analytics/algorithms/stats` - Algorithm statistics
- `GET /api/v1/quantum/analytics/operations/trends` - Operation trends
- `GET /api/v1/quantum/analytics/dashboard/summary` - Dashboard summary

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+
- Redis 7+

### Running with Docker

1. Create the MAMS network:
```bash
docker network create mams-network
```

2. Start the service:
```bash
docker-compose up -d
```

3. Check health:
```bash
curl http://localhost:8020/health
```

### Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/quantum_encryption
export REDIS_URL=redis://localhost:6379/0
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the service:
```bash
uvicorn src.main:app --reload --port 8020
```

## Usage Examples

### Create a Quantum Key

```bash
curl -X POST http://localhost:8020/api/v1/quantum/keys \
  -H "Content-Type: application/json" \
  -d '{
    "key_type": "hybrid",
    "algorithm": "kyber1024",
    "owner_id": "user123",
    "purpose": "data-encryption",
    "enable_hybrid": true,
    "classical_algorithm": "ecc_p384",
    "security_level": 3
  }'
```

### Encrypt Data

```bash
curl -X POST http://localhost:8020/api/v1/quantum/keys/encrypt \
  -H "Content-Type: application/json" \
  -d '{
    "data": "SGVsbG8gV29ybGQ=",
    "key_id": "qk_kyber1024_abc123",
    "use_hybrid": true
  }'
```

### Sign Data

```bash
curl -X POST http://localhost:8020/api/v1/quantum/keys/sign \
  -H "Content-Type: application/json" \
  -d '{
    "data": "SGVsbG8gV29ybGQ=",
    "key_id": "qk_dilithium5_def456",
    "hash_algorithm": "SHA3-512"
  }'
```

## Configuration

Key configuration options in environment variables:

- `QUANTUM_KEY_SIZE`: Default key size in bits (default: 256)
- `ENABLE_HYBRID_MODE`: Enable hybrid classical-quantum encryption (default: true)
- `KEY_ROTATION_DAYS`: Days before key rotation is required (default: 90)
- `MAX_KEY_AGE_DAYS`: Maximum key age before expiration (default: 365)
- `DEFAULT_KEM_ALGORITHM`: Default KEM algorithm (default: kyber1024)
- `DEFAULT_SIGNATURE_ALGORITHM`: Default signature algorithm (default: dilithium5)

## Security Considerations

1. **Key Storage**: Private keys are encrypted at rest using a Key Encryption Key (KEK)
2. **Access Control**: Role-based access control for key operations
3. **Audit Logging**: All cryptographic operations are logged
4. **Key Rotation**: Automated key rotation with data migration
5. **Quantum Resistance**: All algorithms meet NIST post-quantum security levels

## Migration Path

### From Classical to Quantum

1. Enable hybrid mode to use both classical and quantum algorithms
2. Gradually migrate keys using the migration planning API
3. Monitor security assessment scores
4. Phase out classical-only keys

### Algorithm Migration

```bash
curl -X POST http://localhost:8020/api/v1/quantum/analytics/migration/plan \
  -H "Content-Type: application/json" \
  -d '{
    "source_algorithm": "rsa2048",
    "target_algorithm": "kyber1024",
    "dry_run": true
  }'
```

## Performance

- Average operation time: < 10ms for most algorithms
- Batch processing: Up to 1000 operations per request
- Concurrent operations: Configurable (default: 100)
- Key caching: Enabled by default for performance

## Monitoring

### Prometheus Metrics
Available at `/metrics`:
- `quantum_keys_total`: Total number of keys
- `quantum_operations_total`: Total operations performed
- `quantum_operation_duration_seconds`: Operation latency
- `quantum_key_rotation_compliance`: Rotation compliance percentage

### Health Check
```bash
curl http://localhost:8020/health
```

### Capabilities
```bash
curl http://localhost:8020/api/v1/quantum/capabilities
```

## Development

### Running Tests
```bash
pytest tests/ -v --cov=src
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure PostgreSQL and Redis are running
2. **Migration Errors**: Check database permissions and connection string
3. **Performance Issues**: Enable key caching and check concurrent operation limits
4. **Key Expiration**: Monitor expiring keys and enable automatic rotation

### Debug Mode
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## Future Enhancements

- [ ] Hardware Security Module (HSM) integration
- [ ] Quantum Random Number Generator (QRNG) support
- [ ] Distributed key management
- [ ] Multi-party computation support
- [ ] Homomorphic encryption capabilities

## References

- [NIST Post-Quantum Cryptography](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [CRYSTALS Suite](https://pq-crystals.org/)
- [Open Quantum Safe](https://openquantumsafe.org/)
- [ETSI Quantum Safe Cryptography](https://www.etsi.org/technologies/quantum-safe-cryptography)

## License

Part of the MAMS platform. See main project for license details.