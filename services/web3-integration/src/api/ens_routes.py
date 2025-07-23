"""ENS (Ethereum Name Service) routes for Web3 Integration Service"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.base import get_db
from ..models.schemas import ENSResolveResponse, ENSReverseResolveResponse, ENSMetadataResponse
from ..services.web3_connector import Web3ConnectorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ens", tags=["ens"])

@router.get("/resolve/{ens_name}", response_model=ENSResolveResponse)
async def resolve_ens_name(
    ens_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Resolve an ENS name to an Ethereum address"""
    try:
        # Validate ENS name format
        if not ens_name.endswith('.eth'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ENS name format"
            )
        
        connector = Web3ConnectorService()
        address = await connector.get_address_from_ens(ens_name)
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ENS name not found"
            )
        
        # Get additional ENS metadata
        metadata = await connector.get_ens_metadata(ens_name)
        
        return ENSResolveResponse(
            ens_name=ens_name,
            address=address,
            resolved=True,
            metadata=metadata or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving ENS name {ens_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve ENS name"
        )

@router.get("/reverse/{address}", response_model=ENSReverseResolveResponse)
async def reverse_resolve_address(
    address: str,
    db: AsyncSession = Depends(get_db)
):
    """Reverse resolve an Ethereum address to its ENS name"""
    try:
        connector = Web3ConnectorService()
        
        # Validate address format
        if not connector.is_valid_address(address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Ethereum address"
            )
        
        ens_name = await connector.get_ens_name(address)
        
        result = ENSReverseResolveResponse(
            address=address,
            ens_name=ens_name,
            resolved=bool(ens_name)
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reverse resolving address {address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reverse resolve address"
        )

@router.get("/metadata/{ens_name}", response_model=ENSMetadataResponse)
async def get_ens_metadata(
    ens_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get metadata associated with an ENS name"""
    try:
        # Validate ENS name format
        if not ens_name.endswith('.eth'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ENS name format"
            )
        
        connector = Web3ConnectorService()
        
        # First check if ENS name exists
        address = await connector.get_address_from_ens(ens_name)
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ENS name not found"
            )
        
        # Get metadata
        metadata = await connector.get_ens_metadata(ens_name)
        
        return ENSMetadataResponse(
            ens_name=ens_name,
            address=address,
            metadata=metadata or {},
            avatar=metadata.get("avatar") if metadata else None,
            description=metadata.get("description") if metadata else None,
            url=metadata.get("url") if metadata else None,
            twitter=metadata.get("com.twitter") if metadata else None,
            github=metadata.get("com.github") if metadata else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ENS metadata for {ens_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ENS metadata"
        )

@router.get("/check-availability/{ens_name}")
async def check_ens_availability(
    ens_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if an ENS name is available for registration"""
    try:
        # Validate ENS name format
        if not ens_name.endswith('.eth'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ENS name format"
            )
        
        connector = Web3ConnectorService()
        
        # Check if name is available
        is_available = await connector.check_ens_availability(ens_name)
        
        return {
            "ens_name": ens_name,
            "available": is_available,
            "registration_cost": None  # Would need to query ENS registrar
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking ENS availability for {ens_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check ENS availability"
        )

@router.post("/batch-resolve")
async def batch_resolve_ens_names(
    ens_names: list[str],
    db: AsyncSession = Depends(get_db)
):
    """Batch resolve multiple ENS names"""
    try:
        if len(ens_names) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 ENS names per batch request"
            )
        
        connector = Web3ConnectorService()
        results = {}
        
        for ens_name in ens_names:
            try:
                if ens_name.endswith('.eth'):
                    address = await connector.get_address_from_ens(ens_name)
                    results[ens_name] = {
                        "address": address,
                        "resolved": bool(address)
                    }
                else:
                    results[ens_name] = {
                        "address": None,
                        "resolved": False,
                        "error": "Invalid ENS name format"
                    }
            except Exception as e:
                results[ens_name] = {
                    "address": None,
                    "resolved": False,
                    "error": str(e)
                }
        
        return {"results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch resolving ENS names: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch resolve ENS names"
        )

@router.post("/batch-reverse-resolve")
async def batch_reverse_resolve_addresses(
    addresses: list[str],
    db: AsyncSession = Depends(get_db)
):
    """Batch reverse resolve multiple Ethereum addresses"""
    try:
        if len(addresses) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 addresses per batch request"
            )
        
        connector = Web3ConnectorService()
        results = {}
        
        for address in addresses:
            try:
                if connector.is_valid_address(address):
                    ens_name = await connector.get_ens_name(address)
                    results[address] = {
                        "ens_name": ens_name,
                        "resolved": bool(ens_name)
                    }
                else:
                    results[address] = {
                        "ens_name": None,
                        "resolved": False,
                        "error": "Invalid Ethereum address"
                    }
            except Exception as e:
                results[address] = {
                    "ens_name": None,
                    "resolved": False,
                    "error": str(e)
                }
        
        return {"results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch reverse resolving addresses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch reverse resolve addresses"
        )