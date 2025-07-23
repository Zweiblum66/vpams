"""
Blockchain API Routes for Rights Management Service
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.logger import get_logger
from ..models.schemas import User
from ..models.blockchain_schemas import (
    BlockchainConfigCreate, BlockchainConfigUpdate, BlockchainConfigResponse,
    BlockCreate, BlockResponse,
    TransactionCreate, TransactionResponse,
    RightsBlockchainRecord, BlockchainQuery, BlockchainVerification,
    BlockchainStats,
    SmartContractCreate, SmartContractUpdate, SmartContractResponse,
    ContractInteraction, ContractInteractionResult,
    IPFSUpload, IPFSResponse,
    BlockchainType, TransactionStatus, BlockchainNetwork
)
from ..services.blockchain_service import BlockchainService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/blockchain", tags=["blockchain"])

# Initialize blockchain service
blockchain_service = BlockchainService()


@router.on_event("startup")
async def startup_event():
    """Initialize blockchain service on startup"""
    await blockchain_service.initialize()


# Configuration endpoints
@router.post("/config", response_model=BlockchainConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_blockchain_config(
    config_data: BlockchainConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create blockchain configuration"""
    try:
        # Check admin permission
        if "admin" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        
        logger.info(f"Creating blockchain config: {config_data.blockchain_type}")
        result = await blockchain_service.create_blockchain_config(db, config_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create blockchain config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create blockchain config: {str(e)}"
        )


@router.put("/config/{config_id}", response_model=BlockchainConfigResponse)
async def update_blockchain_config(
    config_id: str,
    update_data: BlockchainConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update blockchain configuration"""
    try:
        # Check admin permission
        if "admin" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        
        result = await blockchain_service.update_blockchain_config(db, config_id, update_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update blockchain config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update blockchain config: {str(e)}"
        )


# Transaction endpoints
@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    config_id: str = Query(..., description="Blockchain configuration ID"),
    transaction_data: TransactionCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a blockchain transaction"""
    try:
        logger.info(f"Creating transaction: {transaction_data.transaction_type}")
        
        result = await blockchain_service.create_transaction(
            db, config_id, transaction_data, current_user.user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transaction details"""
    try:
        # Implementation would fetch transaction details
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Get transaction endpoint not yet implemented"
        )
        
    except Exception as e:
        logger.error(f"Failed to get transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction: {str(e)}"
        )


# Rights record endpoints
@router.post("/rights", response_model=dict, status_code=status.HTTP_201_CREATED)
async def store_rights_on_blockchain(
    config_id: str = Query(..., description="Blockchain configuration ID"),
    record_data: RightsBlockchainRecord = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Store rights record on blockchain"""
    try:
        logger.info(f"Storing rights record for: {record_data.entity_type}/{record_data.entity_id}")
        
        result = await blockchain_service.store_rights_record(
            db, config_id, record_data, current_user.user_id
        )
        
        return {
            "message": "Rights record stored successfully",
            "record_id": str(result.id),
            "hash": result.data_hash,
            "transaction_id": str(result.transaction_id) if result.transaction_id else None
        }
        
    except Exception as e:
        logger.error(f"Failed to store rights record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store rights record: {str(e)}"
        )


@router.get("/rights/verify", response_model=BlockchainVerification)
async def verify_rights_record(
    entity_type: str = Query(..., description="Entity type"),
    entity_id: str = Query(..., description="Entity ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify rights record on blockchain"""
    try:
        logger.info(f"Verifying rights record: {entity_type}/{entity_id}")
        
        result = await blockchain_service.verify_rights_record(db, entity_type, entity_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to verify rights record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify rights record: {str(e)}"
        )


@router.post("/rights/query", response_model=List[dict])
async def query_rights_records(
    query_params: BlockchainQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Query rights records from blockchain"""
    try:
        # Implementation would query blockchain records
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Query rights records endpoint not yet implemented"
        )
        
    except Exception as e:
        logger.error(f"Failed to query rights records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query rights records: {str(e)}"
        )


# Block endpoints (for private blockchain)
@router.post("/blocks", response_model=BlockResponse, status_code=status.HTTP_201_CREATED)
async def create_block(
    config_id: str = Query(..., description="Blockchain configuration ID"),
    block_data: BlockCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new block (private blockchain only)"""
    try:
        logger.info("Creating new block")
        
        result = await blockchain_service.create_block(db, config_id, block_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create block: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create block: {str(e)}"
        )


# Smart contract endpoints
@router.post("/contracts", response_model=SmartContractResponse, status_code=status.HTTP_201_CREATED)
async def deploy_smart_contract(
    contract_data: SmartContractCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deploy a smart contract"""
    try:
        # Check admin permission for contract deployment
        if "admin" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for contract deployment"
            )
        
        logger.info(f"Deploying smart contract: {contract_data.contract_name}")
        
        result = await blockchain_service.deploy_smart_contract(
            db, contract_data, current_user.user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to deploy smart contract: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy smart contract: {str(e)}"
        )


@router.post("/contracts/{contract_id}/interact", response_model=ContractInteractionResult)
async def interact_with_contract(
    contract_id: str,
    interaction_data: ContractInteraction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Interact with a smart contract"""
    try:
        # Update interaction data with contract ID
        interaction_data.contract_id = contract_id
        
        logger.info(f"Interacting with contract {contract_id}: {interaction_data.method_name}")
        
        result = await blockchain_service.interact_with_contract(
            db, interaction_data, current_user.user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to interact with contract: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to interact with contract: {str(e)}"
        )


# IPFS endpoints
@router.post("/ipfs/upload", response_model=IPFSResponse)
async def upload_to_ipfs(
    upload_data: IPFSUpload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload data to IPFS"""
    try:
        logger.info("Uploading data to IPFS")
        
        result = await blockchain_service.upload_to_ipfs(db, upload_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to upload to IPFS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to IPFS: {str(e)}"
        )


@router.get("/ipfs/{ipfs_hash}")
async def get_from_ipfs(
    ipfs_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve data from IPFS"""
    try:
        # Implementation would retrieve and decrypt IPFS data
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Get from IPFS endpoint not yet implemented"
        )
        
    except Exception as e:
        logger.error(f"Failed to get from IPFS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get from IPFS: {str(e)}"
        )


# Statistics endpoints
@router.get("/stats", response_model=BlockchainStats)
async def get_blockchain_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get blockchain statistics"""
    try:
        logger.info("Getting blockchain statistics")
        
        result = await blockchain_service.get_blockchain_stats(db, start_date, end_date)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get blockchain stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blockchain stats: {str(e)}"
        )


# Health check
@router.get("/health")
async def blockchain_health_check():
    """Blockchain service health check"""
    return {
        "status": "healthy",
        "service": "blockchain",
        "features": {
            "ethereum": True,
            "hyperledger": False,  # Not yet implemented
            "ipfs": True,
            "private_blockchain": True,
            "smart_contracts": True
        }
    }