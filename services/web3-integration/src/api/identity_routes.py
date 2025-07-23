"""Decentralized Identity (DID) routes"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from ..core.config import settings
from ..db.base import get_db
from ..models.web3_models import Web3User, DecentralizedStorage
from ..models.schemas import (
    DIDDocument,
    DIDCreateRequest,
    DIDUpdateRequest,
    VerifiableCredential,
    VerifiablePresentation,
    DIDResolutionResponse
)
from ..services.did_service import DIDService
from ..services.ipfs_service import IPFSService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/did/create", response_model=DIDDocument)
async def create_did(
    request: DIDCreateRequest,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new Decentralized Identifier (DID)"""
    try:
        did_service = DIDService()
        
        # Create DID based on method
        if request.method == "ethr":
            # Ethereum DID
            did = f"did:ethr:{request.address}"
            did_document = await did_service.create_ethr_did(
                address=request.address,
                public_key=request.public_key,
                services=request.services
            )
        elif request.method == "web":
            # Web DID
            did = f"did:web:{request.domain}"
            did_document = await did_service.create_web_did(
                domain=request.domain,
                public_key=request.public_key,
                services=request.services
            )
        elif request.method == "key":
            # Key DID
            did_document = await did_service.create_key_did(
                public_key=request.public_key
            )
            did = did_document.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported DID method: {request.method}"
            )
        
        # Store DID document in IPFS
        ipfs_service = IPFSService()
        await ipfs_service.initialize()
        
        ipfs_result = await ipfs_service.add_json(
            did_document.dict(),
            pin=True
        )
        
        if ipfs_result:
            # Store reference in database
            storage = DecentralizedStorage(
                storage_id=f"did_{did}",
                user_id=current_user.id,
                storage_type="ipfs",
                content_hash=ipfs_result,
                filename=f"{did}.json",
                content_type="application/json",
                file_size=len(json.dumps(did_document.dict())),
                is_public=True,
                metadata={
                    "type": "did_document",
                    "did": did,
                    "method": request.method
                }
            )
            db.add(storage)
            await db.commit()
        
        await ipfs_service.cleanup()
        
        return did_document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating DID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create DID"
        )

@router.get("/did/resolve/{did}", response_model=DIDResolutionResponse)
async def resolve_did(
    did: str,
    db: AsyncSession = Depends(get_db)
):
    """Resolve a DID to its document"""
    try:
        did_service = DIDService()
        
        # Try to resolve from universal resolver first
        did_document = await did_service.resolve_did(did)
        
        if not did_document:
            # Try to find in our storage
            storage = await db.execute(
                select(DecentralizedStorage).where(
                    DecentralizedStorage.storage_id == f"did_{did}"
                )
            )
            storage = storage.scalar_one_or_none()
            
            if storage:
                ipfs_service = IPFSService()
                await ipfs_service.initialize()
                
                document_data = await ipfs_service.get_json(storage.content_hash)
                await ipfs_service.cleanup()
                
                if document_data:
                    did_document = DIDDocument(**document_data)
        
        if not did_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DID not found"
            )
        
        return DIDResolutionResponse(
            did_document=did_document,
            did_document_metadata={
                "created": datetime.utcnow().isoformat(),
                "updated": datetime.utcnow().isoformat()
            },
            did_resolution_metadata={
                "content_type": "application/did+ld+json",
                "duration": 100
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving DID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve DID"
        )

@router.put("/did/update", response_model=DIDDocument)
async def update_did(
    request: DIDUpdateRequest,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a DID document"""
    try:
        # Verify ownership
        storage = await db.execute(
            select(DecentralizedStorage).where(
                DecentralizedStorage.storage_id == f"did_{request.did}",
                DecentralizedStorage.user_id == current_user.id
            )
        )
        storage = storage.scalar_one_or_none()
        
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't own this DID"
            )
        
        # Get current document
        ipfs_service = IPFSService()
        await ipfs_service.initialize()
        
        current_doc = await ipfs_service.get_json(storage.content_hash)
        if not current_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DID document not found"
            )
        
        # Update document
        if request.add_service:
            current_doc["service"] = current_doc.get("service", [])
            current_doc["service"].append(request.add_service.dict())
        
        if request.remove_service_id:
            current_doc["service"] = [
                s for s in current_doc.get("service", [])
                if s.get("id") != request.remove_service_id
            ]
        
        if request.add_verification_method:
            current_doc["verificationMethod"] = current_doc.get("verificationMethod", [])
            current_doc["verificationMethod"].append(request.add_verification_method.dict())
        
        # Store updated document
        new_hash = await ipfs_service.add_json(current_doc, pin=True)
        
        # Update storage record
        storage.content_hash = new_hash
        storage.file_size = len(json.dumps(current_doc))
        await db.commit()
        
        await ipfs_service.cleanup()
        
        return DIDDocument(**current_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating DID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update DID"
        )

@router.post("/vc/issue", response_model=VerifiableCredential)
async def issue_verifiable_credential(
    credential: VerifiableCredential,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Issue a Verifiable Credential"""
    try:
        did_service = DIDService()
        
        # Sign the credential
        signed_credential = await did_service.sign_credential(
            credential=credential,
            issuer_private_key=current_user.signing_key  # This would need to be securely managed
        )
        
        # Store in IPFS
        ipfs_service = IPFSService()
        await ipfs_service.initialize()
        
        ipfs_hash = await ipfs_service.add_json(
            signed_credential.dict(),
            pin=True
        )
        
        # Store reference
        storage = DecentralizedStorage(
            storage_id=f"vc_{signed_credential.id}",
            user_id=current_user.id,
            storage_type="ipfs",
            content_hash=ipfs_hash,
            filename=f"vc_{signed_credential.id}.json",
            content_type="application/json",
            file_size=len(json.dumps(signed_credential.dict())),
            is_public=False,
            metadata={
                "type": "verifiable_credential",
                "issuer": signed_credential.issuer,
                "subject": signed_credential.credentialSubject.get("id"),
                "credential_type": signed_credential.type
            }
        )
        db.add(storage)
        await db.commit()
        
        await ipfs_service.cleanup()
        
        return signed_credential
        
    except Exception as e:
        logger.error(f"Error issuing credential: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to issue credential"
        )

@router.post("/vc/verify", response_model=dict)
async def verify_credential(
    credential: VerifiableCredential,
    db: AsyncSession = Depends(get_db)
):
    """Verify a Verifiable Credential"""
    try:
        did_service = DIDService()
        
        # Verify the credential
        is_valid = await did_service.verify_credential(credential)
        
        # Additional checks
        checks = {
            "signature_valid": is_valid,
            "not_expired": True,
            "not_revoked": True,
            "issuer_trusted": True
        }
        
        # Check expiration
        if credential.expirationDate:
            expiration = datetime.fromisoformat(credential.expirationDate.replace('Z', '+00:00'))
            checks["not_expired"] = expiration > datetime.utcnow()
        
        # Check revocation (would need revocation registry)
        # checks["not_revoked"] = await check_revocation(credential.id)
        
        return {
            "verified": all(checks.values()),
            "checks": checks,
            "credential_id": credential.id,
            "issuer": credential.issuer,
            "subject": credential.credentialSubject.get("id")
        }
        
    except Exception as e:
        logger.error(f"Error verifying credential: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify credential"
        )

@router.post("/vp/create", response_model=VerifiablePresentation)
async def create_presentation(
    credentials: List[VerifiableCredential],
    challenge: str,
    domain: str,
    current_user: Web3User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a Verifiable Presentation"""
    try:
        did_service = DIDService()
        
        # Create presentation
        presentation = await did_service.create_presentation(
            credentials=credentials,
            holder_did=current_user.did,
            challenge=challenge,
            domain=domain,
            holder_private_key=current_user.signing_key
        )
        
        return presentation
        
    except Exception as e:
        logger.error(f"Error creating presentation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create presentation"
        )

@router.post("/vp/verify", response_model=dict)
async def verify_presentation(
    presentation: VerifiablePresentation,
    expected_challenge: str,
    expected_domain: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify a Verifiable Presentation"""
    try:
        did_service = DIDService()
        
        # Verify the presentation
        is_valid = await did_service.verify_presentation(
            presentation=presentation,
            challenge=expected_challenge,
            domain=expected_domain
        )
        
        # Verify each credential in the presentation
        credential_results = []
        for credential in presentation.verifiableCredential:
            cred_valid = await did_service.verify_credential(credential)
            credential_results.append({
                "id": credential.id,
                "valid": cred_valid,
                "type": credential.type
            })
        
        return {
            "verified": is_valid and all(c["valid"] for c in credential_results),
            "presentation_valid": is_valid,
            "holder": presentation.holder,
            "credentials": credential_results,
            "challenge_match": presentation.proof.get("challenge") == expected_challenge,
            "domain_match": presentation.proof.get("domain") == expected_domain
        }
        
    except Exception as e:
        logger.error(f"Error verifying presentation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify presentation"
        )

# Helper function to get current user (would be implemented with JWT)
async def get_current_user(db: AsyncSession = Depends(get_db)) -> Web3User:
    # This would validate JWT and return user
    # For now, returning a placeholder
    raise NotImplementedError("Authentication required")