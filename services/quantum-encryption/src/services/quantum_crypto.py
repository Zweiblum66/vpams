import base64
import hashlib
import secrets
import json
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ..models.quantum_key import (
    QuantumKey, KeyType, KeyStatus, AlgorithmType, 
    QuantumOperation, EncryptedData
)
from ..models.schemas import SecurityLevel
from ..core.config import settings

logger = logging.getLogger(__name__)

class QuantumCryptoService:
    """Service for quantum-resistant cryptographic operations."""
    
    def __init__(self):
        self.backend = default_backend()
        self._algorithm_map = {
            # Classical algorithms for hybrid mode
            AlgorithmType.RSA2048: self._generate_rsa_2048,
            AlgorithmType.RSA4096: self._generate_rsa_4096,
            AlgorithmType.ECC_P256: self._generate_ecc_p256,
            AlgorithmType.ECC_P384: self._generate_ecc_p384,
            AlgorithmType.ECC_P521: self._generate_ecc_p521,
            AlgorithmType.AES256: self._generate_aes_256,
        }
        
        # Security level mapping
        self._security_levels = {
            AlgorithmType.KYBER512: SecurityLevel.LEVEL_1,
            AlgorithmType.KYBER768: SecurityLevel.LEVEL_2,
            AlgorithmType.KYBER1024: SecurityLevel.LEVEL_3,
            AlgorithmType.DILITHIUM2: SecurityLevel.LEVEL_1,
            AlgorithmType.DILITHIUM3: SecurityLevel.LEVEL_3,
            AlgorithmType.DILITHIUM5: SecurityLevel.LEVEL_5,
            AlgorithmType.FALCON512: SecurityLevel.LEVEL_1,
            AlgorithmType.FALCON1024: SecurityLevel.LEVEL_5,
        }
        
    async def generate_key_pair(
        self,
        db: AsyncSession,
        algorithm: AlgorithmType,
        owner_id: str,
        purpose: Optional[str] = None,
        enable_hybrid: bool = True,
        classical_algorithm: Optional[AlgorithmType] = None
    ) -> QuantumKey:
        """Generate a quantum-resistant key pair."""
        try:
            # Generate unique key ID
            key_id = f"qk_{algorithm.value}_{uuid.uuid4().hex[:12]}"
            
            # Determine key type
            key_type = KeyType.HYBRID if enable_hybrid else KeyType.KEM
            if algorithm in [AlgorithmType.DILITHIUM2, AlgorithmType.DILITHIUM3, 
                           AlgorithmType.DILITHIUM5, AlgorithmType.FALCON512, 
                           AlgorithmType.FALCON1024]:
                key_type = KeyType.HYBRID if enable_hybrid else KeyType.SIGNATURE
                
            # Generate quantum-resistant keys (simulated)
            public_key, private_key, key_size = await self._generate_quantum_keys(algorithm)
            
            # Generate classical keys if hybrid mode
            classical_pub = None
            classical_priv = None
            if enable_hybrid and classical_algorithm:
                classical_pub, classical_priv = await self._generate_classical_keys(
                    classical_algorithm
                )
                
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(days=settings.max_key_age_days)
            
            # Create key record
            quantum_key = QuantumKey(
                key_id=key_id,
                key_type=key_type,
                algorithm=algorithm,
                key_size=key_size,
                public_key=public_key,
                private_key_encrypted=await self._encrypt_private_key(private_key),
                classical_algorithm=classical_algorithm if enable_hybrid else None,
                classical_public_key=classical_pub,
                classical_private_key_encrypted=await self._encrypt_private_key(classical_priv) if classical_priv else None,
                owner_id=owner_id,
                purpose=purpose,
                status=KeyStatus.ACTIVE,
                expires_at=expires_at,
                security_level=self._security_levels.get(algorithm, 3),
                quantum_resistance_score=self._calculate_quantum_resistance_score(algorithm)
            )
            
            db.add(quantum_key)
            await db.commit()
            await db.refresh(quantum_key)
            
            logger.info(f"Generated quantum key {key_id} with algorithm {algorithm}")
            return quantum_key
            
        except Exception as e:
            logger.error(f"Failed to generate quantum key: {str(e)}")
            await db.rollback()
            raise
            
    async def encrypt_data(
        self,
        db: AsyncSession,
        data: bytes,
        key_id: str,
        user_id: str,
        use_hybrid: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]:
        """Encrypt data using quantum-resistant encryption."""
        try:
            # Get the key
            key = await self._get_active_key(db, key_id)
            if not key:
                raise ValueError(f"Key {key_id} not found or inactive")
                
            # Generate operation ID
            operation_id = f"op_enc_{uuid.uuid4().hex[:12]}"
            
            # Encrypt data
            if use_hybrid and key.classical_algorithm:
                # Hybrid encryption: use quantum for key exchange, classical for bulk encryption
                encrypted_data = await self._hybrid_encrypt(data, key)
            else:
                # Pure quantum encryption (simulated)
                encrypted_data = await self._quantum_encrypt(data, key)
                
            # Record operation
            operation = QuantumOperation(
                operation_id=operation_id,
                operation_type="encrypt",
                key_id=key.id,
                user_id=user_id,
                input_size=len(data),
                output_size=len(encrypted_data),
                algorithm_used=key.algorithm,
                success=True,
                metadata=metadata
            )
            
            db.add(operation)
            
            # Update key usage
            key.last_used_at = datetime.utcnow()
            
            await db.commit()
            
            return encrypted_data, operation_id
            
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            await db.rollback()
            raise
            
    async def decrypt_data(
        self,
        db: AsyncSession,
        encrypted_data: bytes,
        key_id: str,
        user_id: str,
        operation_id: Optional[str] = None
    ) -> bytes:
        """Decrypt data using quantum-resistant decryption."""
        try:
            # Get the key
            key = await self._get_active_key(db, key_id)
            if not key:
                raise ValueError(f"Key {key_id} not found or inactive")
                
            # Generate operation ID if not provided
            if not operation_id:
                operation_id = f"op_dec_{uuid.uuid4().hex[:12]}"
                
            # Decrypt data
            if key.key_type == KeyType.HYBRID and key.classical_algorithm:
                decrypted_data = await self._hybrid_decrypt(encrypted_data, key)
            else:
                decrypted_data = await self._quantum_decrypt(encrypted_data, key)
                
            # Record operation
            operation = QuantumOperation(
                operation_id=operation_id,
                operation_type="decrypt",
                key_id=key.id,
                user_id=user_id,
                input_size=len(encrypted_data),
                output_size=len(decrypted_data),
                algorithm_used=key.algorithm,
                success=True
            )
            
            db.add(operation)
            
            # Update key usage
            key.last_used_at = datetime.utcnow()
            
            await db.commit()
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            await db.rollback()
            raise
            
    async def sign_data(
        self,
        db: AsyncSession,
        data: bytes,
        key_id: str,
        user_id: str,
        hash_algorithm: str = "SHA3-512"
    ) -> Tuple[bytes, str]:
        """Sign data using quantum-resistant signature."""
        try:
            # Get the key
            key = await self._get_active_key(db, key_id)
            if not key:
                raise ValueError(f"Key {key_id} not found or inactive")
                
            # Check if key supports signatures
            if key.algorithm not in [AlgorithmType.DILITHIUM2, AlgorithmType.DILITHIUM3,
                                   AlgorithmType.DILITHIUM5, AlgorithmType.FALCON512,
                                   AlgorithmType.FALCON1024, AlgorithmType.SPHINCS_SHA256_128F,
                                   AlgorithmType.SPHINCS_SHA256_192F, AlgorithmType.SPHINCS_SHA256_256F]:
                raise ValueError(f"Key algorithm {key.algorithm} does not support signatures")
                
            # Generate operation ID
            operation_id = f"op_sign_{uuid.uuid4().hex[:12]}"
            
            # Hash the data
            hashed_data = await self._hash_data(data, hash_algorithm)
            
            # Sign data (simulated quantum signature)
            signature = await self._quantum_sign(hashed_data, key)
            
            # Record operation
            operation = QuantumOperation(
                operation_id=operation_id,
                operation_type="sign",
                key_id=key.id,
                user_id=user_id,
                input_size=len(data),
                output_size=len(signature),
                algorithm_used=key.algorithm,
                success=True,
                metadata={"hash_algorithm": hash_algorithm}
            )
            
            db.add(operation)
            
            # Update key usage
            key.last_used_at = datetime.utcnow()
            
            await db.commit()
            
            return signature, operation_id
            
        except Exception as e:
            logger.error(f"Signing failed: {str(e)}")
            await db.rollback()
            raise
            
    async def verify_signature(
        self,
        db: AsyncSession,
        data: bytes,
        signature: bytes,
        key_id: str,
        user_id: str,
        hash_algorithm: str = "SHA3-512"
    ) -> bool:
        """Verify a quantum-resistant signature."""
        try:
            # Get the key
            key = await self._get_active_key(db, key_id)
            if not key:
                raise ValueError(f"Key {key_id} not found or inactive")
                
            # Generate operation ID
            operation_id = f"op_verify_{uuid.uuid4().hex[:12]}"
            
            # Hash the data
            hashed_data = await self._hash_data(data, hash_algorithm)
            
            # Verify signature (simulated quantum verification)
            is_valid = await self._quantum_verify(hashed_data, signature, key)
            
            # Record operation
            operation = QuantumOperation(
                operation_id=operation_id,
                operation_type="verify",
                key_id=key.id,
                user_id=user_id,
                input_size=len(data),
                algorithm_used=key.algorithm,
                success=is_valid,
                metadata={"hash_algorithm": hash_algorithm}
            )
            
            db.add(operation)
            await db.commit()
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            await db.rollback()
            raise
            
    # Private helper methods
    async def _generate_quantum_keys(self, algorithm: AlgorithmType) -> Tuple[str, str, int]:
        """Generate quantum-resistant keys (simulated)."""
        # In production, this would use actual quantum-resistant libraries
        # For now, we simulate with random data
        
        key_sizes = {
            AlgorithmType.KYBER512: 1632,
            AlgorithmType.KYBER768: 2400,
            AlgorithmType.KYBER1024: 3168,
            AlgorithmType.DILITHIUM2: 2528,
            AlgorithmType.DILITHIUM3: 4000,
            AlgorithmType.DILITHIUM5: 4864,
            AlgorithmType.FALCON512: 897,
            AlgorithmType.FALCON1024: 1793,
        }
        
        key_size = key_sizes.get(algorithm, 2048)
        
        # Generate random keys (simulation)
        private_key = secrets.token_bytes(key_size // 8)
        public_key = secrets.token_bytes(key_size // 8)
        
        # Encode as base64
        private_key_b64 = base64.b64encode(private_key).decode()
        public_key_b64 = base64.b64encode(public_key).decode()
        
        return public_key_b64, private_key_b64, key_size
        
    async def _generate_classical_keys(self, algorithm: AlgorithmType) -> Tuple[str, str]:
        """Generate classical keys for hybrid mode."""
        if algorithm in self._algorithm_map:
            return await self._algorithm_map[algorithm]()
        else:
            raise ValueError(f"Unsupported classical algorithm: {algorithm}")
            
    async def _generate_rsa_2048(self) -> Tuple[str, str]:
        """Generate RSA 2048-bit keys."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=self.backend
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return public_pem.decode(), private_pem.decode()
        
    async def _generate_rsa_4096(self) -> Tuple[str, str]:
        """Generate RSA 4096-bit keys."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=self.backend
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return public_pem.decode(), private_pem.decode()
        
    async def _generate_ecc_p256(self) -> Tuple[str, str]:
        """Generate ECC P-256 keys."""
        private_key = ec.generate_private_key(ec.SECP256R1(), self.backend)
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return public_pem.decode(), private_pem.decode()
        
    async def _generate_ecc_p384(self) -> Tuple[str, str]:
        """Generate ECC P-384 keys."""
        private_key = ec.generate_private_key(ec.SECP384R1(), self.backend)
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return public_pem.decode(), private_pem.decode()
        
    async def _generate_ecc_p521(self) -> Tuple[str, str]:
        """Generate ECC P-521 keys."""
        private_key = ec.generate_private_key(ec.SECP521R1(), self.backend)
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return public_pem.decode(), private_pem.decode()
        
    async def _generate_aes_256(self) -> Tuple[str, str]:
        """Generate AES 256-bit key."""
        key = secrets.token_bytes(32)  # 256 bits
        key_b64 = base64.b64encode(key).decode()
        return key_b64, key_b64  # Symmetric key
        
    async def _encrypt_private_key(self, private_key: Optional[str]) -> Optional[str]:
        """Encrypt private key for storage."""
        if not private_key:
            return None
            
        # In production, use proper key encryption key (KEK)
        # For now, simple simulation
        return base64.b64encode(private_key.encode()).decode()
        
    async def _decrypt_private_key(self, encrypted_key: Optional[str]) -> Optional[str]:
        """Decrypt private key from storage."""
        if not encrypted_key:
            return None
            
        # In production, use proper key encryption key (KEK)
        # For now, simple simulation
        return base64.b64decode(encrypted_key).decode()
        
    async def _get_active_key(self, db: AsyncSession, key_id: str) -> Optional[QuantumKey]:
        """Get an active key by ID."""
        result = await db.execute(
            select(QuantumKey).where(
                and_(
                    QuantumKey.key_id == key_id,
                    QuantumKey.status == KeyStatus.ACTIVE
                )
            )
        )
        return result.scalar_one_or_none()
        
    async def _hybrid_encrypt(self, data: bytes, key: QuantumKey) -> bytes:
        """Perform hybrid encryption."""
        # Generate ephemeral symmetric key
        symmetric_key = secrets.token_bytes(32)  # 256-bit key
        
        # Encrypt data with symmetric key (AES-GCM)
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        cipher = Cipher(
            algorithms.AES(symmetric_key),
            modes.GCM(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Simulate quantum KEM to encrypt symmetric key
        # In production, use actual quantum KEM
        encrypted_symmetric_key = base64.b64encode(symmetric_key).decode()
        
        # Combine components
        result = {
            "iv": base64.b64encode(iv).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "tag": base64.b64encode(encryptor.tag).decode(),
            "encrypted_key": encrypted_symmetric_key,
            "algorithm": key.algorithm.value
        }
        
        return json.dumps(result).encode()
        
    async def _hybrid_decrypt(self, encrypted_data: bytes, key: QuantumKey) -> bytes:
        """Perform hybrid decryption."""
        # Parse encrypted data
        data = json.loads(encrypted_data.decode())
        
        # Simulate quantum KEM to decrypt symmetric key
        # In production, use actual quantum KEM
        symmetric_key = base64.b64decode(data["encrypted_key"])
        
        # Decrypt data with symmetric key
        iv = base64.b64decode(data["iv"])
        ciphertext = base64.b64decode(data["ciphertext"])
        tag = base64.b64decode(data["tag"])
        
        cipher = Cipher(
            algorithms.AES(symmetric_key),
            modes.GCM(iv, tag),
            backend=self.backend
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext
        
    async def _quantum_encrypt(self, data: bytes, key: QuantumKey) -> bytes:
        """Pure quantum encryption (simulated)."""
        # In production, use actual quantum encryption
        # For now, simulate with XOR and key material
        key_material = base64.b64decode(key.public_key)
        
        # Simple XOR encryption (NOT SECURE - for simulation only)
        encrypted = bytearray()
        for i in range(len(data)):
            encrypted.append(data[i] ^ key_material[i % len(key_material)])
            
        return bytes(encrypted)
        
    async def _quantum_decrypt(self, encrypted_data: bytes, key: QuantumKey) -> bytes:
        """Pure quantum decryption (simulated)."""
        # In production, use actual quantum decryption
        # For now, simulate with XOR (same as encryption for XOR)
        private_key = await self._decrypt_private_key(key.private_key_encrypted)
        key_material = base64.b64decode(private_key)
        
        # Simple XOR decryption (NOT SECURE - for simulation only)
        decrypted = bytearray()
        for i in range(len(encrypted_data)):
            decrypted.append(encrypted_data[i] ^ key_material[i % len(key_material)])
            
        return bytes(decrypted)
        
    async def _hash_data(self, data: bytes, algorithm: str) -> bytes:
        """Hash data using specified algorithm."""
        if algorithm == "SHA3-512":
            h = hashlib.sha3_512()
        elif algorithm == "SHA3-384":
            h = hashlib.sha3_384()
        elif algorithm == "SHA3-256":
            h = hashlib.sha3_256()
        elif algorithm == "BLAKE2b":
            h = hashlib.blake2b()
        elif algorithm == "BLAKE2s":
            h = hashlib.blake2s()
        else:
            h = hashlib.sha3_512()  # Default
            
        h.update(data)
        return h.digest()
        
    async def _quantum_sign(self, data: bytes, key: QuantumKey) -> bytes:
        """Quantum signature (simulated)."""
        # In production, use actual quantum signature algorithm
        # For now, simulate with hash and key material
        private_key = await self._decrypt_private_key(key.private_key_encrypted)
        key_material = base64.b64decode(private_key)
        
        # Combine data hash with key material
        signature_input = data + key_material[:64]  # Use first 64 bytes of key
        signature = hashlib.sha3_512(signature_input).digest()
        
        return signature
        
    async def _quantum_verify(self, data: bytes, signature: bytes, key: QuantumKey) -> bool:
        """Quantum signature verification (simulated)."""
        # In production, use actual quantum verification
        # For now, simulate verification
        key_material = base64.b64decode(key.public_key)
        
        # Recreate signature with public key
        signature_input = data + key_material[:64]  # Use first 64 bytes of key
        expected_signature = hashlib.sha3_512(signature_input).digest()
        
        return signature == expected_signature
        
    def _calculate_quantum_resistance_score(self, algorithm: AlgorithmType) -> int:
        """Calculate quantum resistance score (0-100)."""
        scores = {
            # Quantum-resistant algorithms get high scores
            AlgorithmType.KYBER512: 85,
            AlgorithmType.KYBER768: 90,
            AlgorithmType.KYBER1024: 95,
            AlgorithmType.DILITHIUM2: 85,
            AlgorithmType.DILITHIUM3: 90,
            AlgorithmType.DILITHIUM5: 95,
            AlgorithmType.FALCON512: 85,
            AlgorithmType.FALCON1024: 95,
            AlgorithmType.SPHINCS_SHA256_128F: 80,
            AlgorithmType.SPHINCS_SHA256_192F: 85,
            AlgorithmType.SPHINCS_SHA256_256F: 90,
            AlgorithmType.NTRU_HPS2048509: 80,
            AlgorithmType.NTRU_HPS2048677: 85,
            AlgorithmType.NTRU_HPS4096821: 90,
            AlgorithmType.SABER_LIGHT: 80,
            AlgorithmType.SABER: 85,
            AlgorithmType.SABER_FIRE: 90,
            # Classical algorithms get low scores
            AlgorithmType.RSA2048: 20,
            AlgorithmType.RSA4096: 25,
            AlgorithmType.ECC_P256: 15,
            AlgorithmType.ECC_P384: 20,
            AlgorithmType.ECC_P521: 25,
            AlgorithmType.AES256: 50,  # Symmetric is somewhat resistant
        }
        
        return scores.get(algorithm, 50)