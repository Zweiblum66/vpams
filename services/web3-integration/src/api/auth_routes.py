"""Authentication routes for Web3 Integration Service"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from ..core.config import settings
from ..db.base import get_db
from ..models.web3_models import Web3User, Web3Wallet
from ..models.schemas import (
    SIWEMessage,
    SIWEVerifyRequest,
    Web3AuthResponse,
    Web3UserCreate,
    Web3UserResponse
)
from ..services.web3_connector import Web3ConnectorService
from ..services.auth_service import create_access_token, verify_siwe_message

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/siwe/request-nonce", response_model=dict)
async def request_nonce(
    address: str,
    db: AsyncSession = Depends(get_db)
):
    """Request a nonce for Sign-In with Ethereum"""
    try:
        # Validate address
        connector = Web3ConnectorService()
        if not connector.is_valid_address(address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Ethereum address"
            )
        
        # Generate nonce
        nonce = secrets.token_urlsafe(32)
        
        # Check if user exists
        stmt = select(Web3User).join(Web3Wallet).where(
            Web3Wallet.address == address.lower()
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user's nonce
            user.nonce = nonce
            user.siwe_expires_at = datetime.utcnow() + timedelta(minutes=5)
        else:
            # Create new user if needed
            user = Web3User(
                user_id=f"web3_{address.lower()}",
                primary_address=address.lower(),
                nonce=nonce,
                siwe_expires_at=datetime.utcnow() + timedelta(minutes=5)
            )
            db.add(user)
            
            # Create wallet entry
            wallet = Web3Wallet(
                user_id=user.id,
                address=address.lower(),
                wallet_type="metamask",  # Default, will be updated on verification
                chain_type="ethereum",
                is_primary=True,
                is_verified=False
            )
            db.add(wallet)
        
        await db.commit()
        
        return {
            "nonce": nonce,
            "expires_at": user.siwe_expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error requesting nonce: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate nonce"
        )

@router.post("/siwe/verify", response_model=Web3AuthResponse)
async def verify_siwe(
    request: SIWEVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify Sign-In with Ethereum message"""
    try:
        # Get user by address
        stmt = select(Web3User).join(Web3Wallet).where(
            Web3Wallet.address == request.address.lower()
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check nonce expiry
        if user.siwe_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nonce has expired"
            )
        
        # Verify signature
        message = SIWEMessage(
            domain=request.domain,
            address=request.address,
            statement=request.statement,
            uri=request.uri,
            version=request.version,
            chain_id=request.chain_id,
            nonce=request.nonce,
            issued_at=request.issued_at,
            expiration_time=request.expiration_time,
            not_before=request.not_before,
            request_id=request.request_id,
            resources=request.resources
        )
        
        is_valid = await verify_siwe_message(message, request.signature)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Verify nonce matches
        if user.nonce != request.nonce:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid nonce"
            )
        
        # Clear nonce and update last active
        user.nonce = None
        user.siwe_expires_at = None
        user.last_active_at = datetime.utcnow()
        
        # Update wallet verification status
        wallet = await db.execute(
            select(Web3Wallet).where(
                Web3Wallet.user_id == user.id,
                Web3Wallet.address == request.address.lower()
            )
        )
        wallet = wallet.scalar_one()
        wallet.is_verified = True
        wallet.verified_at = datetime.utcnow()
        
        await db.commit()
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": user.user_id,
                "address": request.address.lower(),
                "type": "web3"
            }
        )
        
        return Web3AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=Web3UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying SIWE: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify signature"
        )

@router.post("/connect-wallet", response_model=Web3UserResponse)
async def connect_wallet(
    address: str,
    wallet_type: str,
    chain_type: str,
    user_id: str,  # MAMS user ID
    db: AsyncSession = Depends(get_db)
):
    """Connect a Web3 wallet to a MAMS user account"""
    try:
        # Validate address
        connector = Web3ConnectorService()
        if not connector.is_valid_address(address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid wallet address"
            )
        
        # Check if wallet already exists
        existing_wallet = await db.execute(
            select(Web3Wallet).where(Web3Wallet.address == address.lower())
        )
        if existing_wallet.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet already connected to another account"
            )
        
        # Get or create Web3 user
        user = await db.execute(
            select(Web3User).where(Web3User.user_id == user_id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            user = Web3User(
                user_id=user_id,
                primary_address=address.lower(),
                preferred_chain=chain_type
            )
            db.add(user)
            await db.flush()
        
        # Create wallet
        wallet = Web3Wallet(
            user_id=user.id,
            address=address.lower(),
            wallet_type=wallet_type,
            chain_type=chain_type,
            is_primary=not bool(user.wallets),  # First wallet is primary
            is_verified=False
        )
        db.add(wallet)
        
        # Get ENS name if on Ethereum
        if chain_type == "ethereum":
            ens_name = await connector.get_ens_name(address)
            if ens_name:
                wallet.ens_name = ens_name
                if not user.ens_name:
                    user.ens_name = ens_name
        
        await db.commit()
        await db.refresh(user)
        
        return Web3UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect wallet"
        )

@router.delete("/disconnect-wallet/{wallet_address}")
async def disconnect_wallet(
    wallet_address: str,
    user_id: str,  # From JWT token
    db: AsyncSession = Depends(get_db)
):
    """Disconnect a wallet from user account"""
    try:
        # Get user
        user = await db.execute(
            select(Web3User).where(Web3User.user_id == user_id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get wallet
        wallet = await db.execute(
            select(Web3Wallet).where(
                Web3Wallet.user_id == user.id,
                Web3Wallet.address == wallet_address.lower()
            )
        )
        wallet = wallet.scalar_one_or_none()
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Check if it's the last wallet
        if len(user.wallets) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot disconnect the last wallet"
            )
        
        # If primary wallet, assign primary to another wallet
        if wallet.is_primary and len(user.wallets) > 1:
            for w in user.wallets:
                if w.id != wallet.id:
                    w.is_primary = True
                    user.primary_address = w.address
                    break
        
        # Delete wallet
        await db.delete(wallet)
        await db.commit()
        
        return {"message": "Wallet disconnected successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect wallet"
        )