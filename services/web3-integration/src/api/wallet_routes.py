"""Wallet management routes"""

import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from ..core.config import settings
from ..db.base import get_db
from ..models.web3_models import (
    Web3User, Web3Wallet, TokenBalance, Web3Transaction,
    ChainType, TransactionStatus
)
from ..models.schemas import (
    WalletInfo,
    WalletBalance,
    TokenBalanceResponse,
    TransactionRequest,
    TransactionResponse,
    GasPriceResponse
)
from ..services.web3_connector import Web3ConnectorService
from ..services.wallet_service import WalletService
from ..services.token_service import TokenService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/wallets", response_model=List[WalletInfo])
async def get_user_wallets(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all wallets for a user"""
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
        
        # Get wallets with balances
        wallets = []
        wallet_service = WalletService()
        
        for wallet in user.wallets:
            # Get native balance
            native_balance = await wallet_service.get_native_balance(
                wallet.chain_type.value,
                wallet.address
            )
            
            wallet_info = WalletInfo(
                id=str(wallet.id),
                address=wallet.address,
                wallet_type=wallet.wallet_type.value,
                chain_type=wallet.chain_type.value,
                label=wallet.label,
                is_primary=wallet.is_primary,
                is_verified=wallet.is_verified,
                ens_name=wallet.ens_name,
                native_balance=str(native_balance) if native_balance else "0",
                created_at=wallet.created_at
            )
            wallets.append(wallet_info)
        
        return wallets
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get wallets"
        )

@router.get("/wallets/{wallet_address}/balance", response_model=WalletBalance)
async def get_wallet_balance(
    wallet_address: str,
    chain: ChainType = Query(...),
    include_tokens: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get wallet balance including tokens"""
    try:
        wallet_service = WalletService()
        token_service = TokenService()
        
        # Get native balance
        native_balance = await wallet_service.get_native_balance(
            chain.value,
            wallet_address
        )
        
        # Get chain info
        connector = Web3ConnectorService()
        chain_info = connector.get_chain_info(chain.value)
        
        response = WalletBalance(
            address=wallet_address,
            chain=chain.value,
            native_balance=str(native_balance) if native_balance else "0",
            native_symbol=chain_info["currency"],
            tokens=[]
        )
        
        # Get token balances if requested
        if include_tokens:
            # Get wallet from DB
            wallet = await db.execute(
                select(Web3Wallet).where(
                    Web3Wallet.address == wallet_address.lower(),
                    Web3Wallet.chain_type == chain
                )
            )
            wallet = wallet.scalar_one_or_none()
            
            if wallet:
                # Get cached token balances
                token_balances = await db.execute(
                    select(TokenBalance).where(
                        TokenBalance.wallet_id == wallet.id
                    )
                )
                
                for balance in token_balances.scalars():
                    response.tokens.append(TokenBalanceResponse(
                        contract_address=balance.contract_address,
                        symbol=balance.symbol,
                        name=balance.name,
                        decimals=balance.decimals,
                        balance=balance.balance,
                        balance_decimal=balance.balance_decimal,
                        usd_price=balance.usd_price,
                        usd_value=balance.usd_value
                    ))
                
                # Update balances if stale (> 5 minutes old)
                if (not balance.last_updated or 
                    (datetime.utcnow() - balance.last_updated).seconds > 300):
                    # This would trigger background update
                    await token_service.update_wallet_tokens(wallet.id, chain.value)
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get wallet balance"
        )

@router.post("/wallets/{wallet_address}/refresh-balances")
async def refresh_wallet_balances(
    wallet_address: str,
    chain: ChainType = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Force refresh wallet balances"""
    try:
        # Get wallet
        wallet = await db.execute(
            select(Web3Wallet).where(
                Web3Wallet.address == wallet_address.lower(),
                Web3Wallet.chain_type == chain
            )
        )
        wallet = wallet.scalar_one_or_none()
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Update token balances
        token_service = TokenService()
        await token_service.update_wallet_tokens(wallet.id, chain.value)
        
        return {"message": "Balance refresh initiated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh balances"
        )

@router.get("/wallets/{wallet_address}/transactions", response_model=List[TransactionResponse])
async def get_wallet_transactions(
    wallet_address: str,
    chain: Optional[ChainType] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """Get wallet transactions"""
    try:
        # Build query
        query = select(Web3Transaction).where(
            (Web3Transaction.from_address == wallet_address.lower()) |
            (Web3Transaction.to_address == wallet_address.lower())
        )
        
        if chain:
            query = query.where(Web3Transaction.chain_type == chain)
        
        query = query.order_by(Web3Transaction.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        # Convert to response
        responses = []
        for tx in transactions:
            responses.append(TransactionResponse(
                id=str(tx.id),
                transaction_hash=tx.transaction_hash,
                chain_type=tx.chain_type.value,
                from_address=tx.from_address,
                to_address=tx.to_address,
                value=tx.value,
                gas_price=tx.gas_price,
                gas_used=tx.gas_used,
                status=tx.status.value,
                block_number=tx.block_number,
                created_at=tx.created_at,
                confirmed_at=tx.confirmed_at,
                description=tx.description,
                category=tx.category
            ))
        
        return responses
        
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transactions"
        )

@router.post("/wallets/set-primary")
async def set_primary_wallet(
    wallet_address: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Set a wallet as primary"""
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
        
        # Update all wallets
        await db.execute(
            update(Web3Wallet)
            .where(Web3Wallet.user_id == user.id)
            .values(is_primary=False)
        )
        
        # Set new primary
        wallet.is_primary = True
        user.primary_address = wallet.address
        
        await db.commit()
        
        return {"message": "Primary wallet updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting primary wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set primary wallet"
        )

@router.get("/gas-prices", response_model=Dict[str, GasPriceResponse])
async def get_gas_prices(
    chains: List[ChainType] = Query([ChainType.ETHEREUM])
):
    """Get current gas prices for multiple chains"""
    try:
        connector = Web3ConnectorService()
        await connector.initialize()
        
        gas_prices = {}
        
        for chain in chains:
            prices = await connector.get_gas_price(chain.value)
            if prices:
                chain_info = connector.get_chain_info(chain.value)
                gas_prices[chain.value] = GasPriceResponse(
                    chain=chain.value,
                    currency=chain_info["currency"],
                    slow=prices["slow"],
                    standard=prices["standard"],
                    fast=prices["fast"],
                    instant=prices["instant"],
                    block_time=12.0 if chain == ChainType.ETHEREUM else 2.0  # Approximate
                )
        
        await connector.cleanup()
        
        return gas_prices
        
    except Exception as e:
        logger.error(f"Error getting gas prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get gas prices"
        )

@router.post("/wallets/import")
async def import_wallet(
    mnemonic: Optional[str] = None,
    private_key: Optional[str] = None,
    wallet_type: str = "imported",
    label: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Import a wallet (mnemonic or private key)"""
    try:
        if not mnemonic and not private_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either mnemonic or private key must be provided"
            )
        
        wallet_service = WalletService()
        
        # Derive address from mnemonic or private key
        if mnemonic:
            addresses = await wallet_service.derive_addresses_from_mnemonic(
                mnemonic,
                count=1
            )
            address = addresses[0]
        else:
            address = await wallet_service.get_address_from_private_key(private_key)
        
        # Check if wallet already exists
        existing = await db.execute(
            select(Web3Wallet).where(Web3Wallet.address == address.lower())
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet already exists"
            )
        
        # Get or create user
        user = await db.execute(
            select(Web3User).where(Web3User.user_id == user_id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            user = Web3User(
                user_id=user_id,
                primary_address=address.lower()
            )
            db.add(user)
            await db.flush()
        
        # Create wallet
        wallet = Web3Wallet(
            user_id=user.id,
            address=address.lower(),
            wallet_type=wallet_type,
            chain_type=ChainType.ETHEREUM,  # Default to Ethereum
            label=label,
            is_primary=not bool(user.wallets),
            is_verified=True,
            verified_at=datetime.utcnow()
        )
        db.add(wallet)
        
        await db.commit()
        
        return {
            "address": address,
            "message": "Wallet imported successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import wallet"
        )

# Helper function to get current user ID from JWT
async def get_current_user_id() -> str:
    # This would extract user ID from JWT token
    # For now, returning a placeholder
    return "current_user_id"