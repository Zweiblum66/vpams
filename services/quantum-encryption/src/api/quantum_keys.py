from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import base64
import logging

from ..db.base import get_db
from ..models.quantum_key import QuantumKey, KeyStatus, AlgorithmType
from ..models.schemas import (
    QuantumKeyCreate, QuantumKeyUpdate, QuantumKeyResponse,
    EncryptRequest, EncryptResponse, DecryptRequest, DecryptResponse,
    SignRequest, SignResponse, VerifyRequest, VerifyResponse,
    KeyRotationRequest, KeyRotationResponse, KeyRotationStatus,
    BatchEncryptRequest, BatchEncryptResponse
)
from ..services.quantum_crypto import QuantumCryptoService
from ..services.key_management import KeyManagementService
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/quantum/keys", tags=["quantum-keys"])

# Service instances
crypto_service = QuantumCryptoService()
key_service = KeyManagementService()

# Dependency for user authentication (placeholder)
async def get_current_user():
    # In production, implement proper authentication
    return {"id": "user123", "role": "admin"}

@router.post("/", response_model=QuantumKeyResponse)
async def create_quantum_key(
    key_data: QuantumKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new quantum-resistant key pair."""
    try:
        key = await crypto_service.generate_key_pair(
            db=db,
            algorithm=key_data.algorithm,
            owner_id=key_data.owner_id or current_user["id"],
            purpose=key_data.purpose,
            enable_hybrid=key_data.enable_hybrid,
            classical_algorithm=key_data.classical_algorithm
        )
        
        return key
        
    except Exception as e:
        logger.error(f"Failed to create quantum key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create quantum key: {str(e)}"
        )

@router.get("/", response_model=List[QuantumKeyResponse])
async def list_quantum_keys(
    owner_id: Optional[str] = Query(None),
    status: Optional[KeyStatus] = Query(None),
    algorithm: Optional[AlgorithmType] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List quantum keys with optional filtering."""
    try:
        query = select(QuantumKey)
        
        # Apply filters
        filters = []
        if owner_id:
            filters.append(QuantumKey.owner_id == owner_id)
        elif current_user["role"] != "admin":
            # Non-admin users can only see their own keys
            filters.append(QuantumKey.owner_id == current_user["id"])
            
        if status:
            filters.append(QuantumKey.status == status)
        if algorithm:
            filters.append(QuantumKey.algorithm == algorithm)
            
        if filters:
            query = query.where(and_(*filters))
            
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        keys = result.scalars().all()
        
        return keys
        
    except Exception as e:
        logger.error(f"Failed to list quantum keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list quantum keys: {str(e)}"
        )

@router.get("/{key_id}", response_model=QuantumKeyResponse)
async def get_quantum_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific quantum key."""
    try:
        result = await db.execute(
            select(QuantumKey).where(QuantumKey.key_id == key_id)
        )
        key = result.scalar_one_or_none()
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key {key_id} not found"
            )
            
        # Check access permissions
        if current_user["role"] != "admin" and key.owner_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
            
        return key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quantum key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quantum key: {str(e)}"
        )

@router.patch("/{key_id}", response_model=QuantumKeyResponse)
async def update_quantum_key(
    key_id: str,
    update_data: QuantumKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a quantum key."""
    try:
        result = await db.execute(
            select(QuantumKey).where(QuantumKey.key_id == key_id)
        )
        key = result.scalar_one_or_none()
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key {key_id} not found"
            )
            
        # Check access permissions
        if current_user["role"] != "admin" and key.owner_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
            
        # Update fields
        if update_data.purpose is not None:
            key.purpose = update_data.purpose
        if update_data.status is not None:
            key.status = update_data.status
            
        await db.commit()
        await db.refresh(key)
        
        return key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update quantum key: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update quantum key: {str(e)}"
        )

@router.post("/encrypt", response_model=EncryptResponse)
async def encrypt_data(
    request: EncryptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Encrypt data using quantum-resistant encryption."""
    try:
        # Decode base64 data
        data = base64.b64decode(request.data)
        
        # Encrypt
        encrypted_data, operation_id = await crypto_service.encrypt_data(
            db=db,
            data=data,
            key_id=request.key_id,
            user_id=current_user["id"],
            use_hybrid=request.use_hybrid,
            metadata=request.metadata
        )
        
        # Get the key to return algorithm info
        result = await db.execute(
            select(QuantumKey).where(QuantumKey.key_id == request.key_id)
        )
        key = result.scalar_one()
        
        return EncryptResponse(
            encrypted_data=base64.b64encode(encrypted_data).decode(),
            encryption_key_id=request.key_id,
            algorithm_used=key.algorithm,
            hybrid_mode=request.use_hybrid and key.classical_algorithm is not None,
            operation_id=operation_id,
            metadata=request.metadata
        )
        
    except Exception as e:
        logger.error(f"Encryption failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption failed: {str(e)}"
        )

@router.post("/decrypt", response_model=DecryptResponse)
async def decrypt_data(
    request: DecryptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Decrypt data using quantum-resistant decryption."""
    try:
        # Decode base64 data
        encrypted_data = base64.b64decode(request.encrypted_data)
        
        # Decrypt
        decrypted_data = await crypto_service.decrypt_data(
            db=db,
            encrypted_data=encrypted_data,
            key_id=request.key_id,
            user_id=current_user["id"],
            operation_id=request.operation_id
        )
        
        return DecryptResponse(
            decrypted_data=base64.b64encode(decrypted_data).decode(),
            operation_id=request.operation_id or "generated",
            verified=True
        )
        
    except Exception as e:
        logger.error(f"Decryption failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decryption failed: {str(e)}"
        )

@router.post("/sign", response_model=SignResponse)
async def sign_data(
    request: SignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Sign data using quantum-resistant signature."""
    try:
        # Decode base64 data
        data = base64.b64decode(request.data)
        
        # Sign
        signature, operation_id = await crypto_service.sign_data(
            db=db,
            data=data,
            key_id=request.key_id,
            user_id=current_user["id"],
            hash_algorithm=request.hash_algorithm
        )
        
        # Get the key to return algorithm info
        result = await db.execute(
            select(QuantumKey).where(QuantumKey.key_id == request.key_id)
        )
        key = result.scalar_one()
        
        return SignResponse(
            signature=base64.b64encode(signature).decode(),
            key_id=request.key_id,
            algorithm_used=key.algorithm,
            hash_algorithm=request.hash_algorithm,
            operation_id=operation_id
        )
        
    except Exception as e:
        logger.error(f"Signing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signing failed: {str(e)}"
        )

@router.post("/verify", response_model=VerifyResponse)
async def verify_signature(
    request: VerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Verify a quantum-resistant signature."""
    try:
        # Decode base64 data
        data = base64.b64decode(request.data)
        signature = base64.b64decode(request.signature)
        
        # Verify
        is_valid = await crypto_service.verify_signature(
            db=db,
            data=data,
            signature=signature,
            key_id=request.key_id,
            user_id=current_user["id"],
            hash_algorithm=request.hash_algorithm
        )
        
        # Get the key to return algorithm info
        result = await db.execute(
            select(QuantumKey).where(QuantumKey.key_id == request.key_id)
        )
        key = result.scalar_one()
        
        return VerifyResponse(
            valid=is_valid,
            key_id=request.key_id,
            algorithm_used=key.algorithm,
            operation_id="verification_complete",
            details="Signature is valid" if is_valid else "Signature verification failed"
        )
        
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )

@router.post("/{key_id}/rotate", response_model=KeyRotationResponse)
async def rotate_key(
    key_id: str,
    request: KeyRotationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Rotate a quantum key."""
    try:
        return await key_service.rotate_key(
            db=db,
            old_key_id=key_id,
            reason=request.reason,
            initiated_by=current_user["id"],
            migrate_data=request.migrate_data
        )
        
    except Exception as e:
        logger.error(f"Key rotation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key rotation failed: {str(e)}"
        )

@router.get("/rotation/{rotation_id}/status", response_model=KeyRotationStatus)
async def get_rotation_status(
    rotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a key rotation."""
    try:
        return await key_service.get_rotation_status(db, rotation_id)
        
    except Exception as e:
        logger.error(f"Failed to get rotation status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rotation status: {str(e)}"
        )

@router.post("/batch/encrypt", response_model=BatchEncryptResponse)
async def batch_encrypt(
    request: BatchEncryptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Encrypt multiple data items in batch."""
    try:
        results = []
        success_count = 0
        failure_count = 0
        start_time = datetime.utcnow()
        
        for item in request.items:
            try:
                # Process individual encryption
                data = base64.b64decode(item.data)
                encrypted_data, operation_id = await crypto_service.encrypt_data(
                    db=db,
                    data=data,
                    key_id=item.key_id,
                    user_id=current_user["id"],
                    use_hybrid=item.use_hybrid,
                    metadata=item.metadata
                )
                
                # Get key info
                result = await db.execute(
                    select(QuantumKey).where(QuantumKey.key_id == item.key_id)
                )
                key = result.scalar_one()
                
                results.append(EncryptResponse(
                    encrypted_data=base64.b64encode(encrypted_data).decode(),
                    encryption_key_id=item.key_id,
                    algorithm_used=key.algorithm,
                    hybrid_mode=item.use_hybrid and key.classical_algorithm is not None,
                    operation_id=operation_id,
                    metadata=item.metadata
                ))
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to encrypt item: {str(e)}")
                failure_count += 1
                # Add failed result
                results.append(EncryptResponse(
                    encrypted_data="",
                    encryption_key_id=item.key_id,
                    algorithm_used=AlgorithmType.KYBER1024,
                    hybrid_mode=False,
                    operation_id="failed",
                    metadata={"error": str(e)}
                ))
                
        total_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return BatchEncryptResponse(
            results=results,
            total_time_ms=total_time_ms,
            success_count=success_count,
            failure_count=failure_count
        )
        
    except Exception as e:
        logger.error(f"Batch encryption failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch encryption failed: {str(e)}"
        )

@router.delete("/{key_id}/revoke")
async def revoke_key(
    key_id: str,
    reason: str = Query(..., description="Reason for revocation"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Revoke a quantum key."""
    try:
        key = await key_service.revoke_key(db, key_id, reason)
        return {"message": f"Key {key_id} revoked successfully", "status": key.status}
        
    except Exception as e:
        logger.error(f"Key revocation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key revocation failed: {str(e)}"
        )