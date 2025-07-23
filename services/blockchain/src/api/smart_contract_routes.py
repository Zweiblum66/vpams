"""
API routes for smart contract functionality.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from ..core.config import settings
from ..db.base import get_db
from ..services.smart_contract_service import SmartContractService
from ..db.models import SmartContract, NetworkType, ContractType

router = APIRouter()

# Initialize smart contract service
smart_contract_service = SmartContractService()


# Pydantic Models
class ContractCompileRequest(BaseModel):
    """Schema for contract compilation request."""
    contract_path: str = Field(..., description="Path to the contract file")
    contract_name: Optional[str] = Field(None, description="Name of the contract to compile")


class ContractDeployRequest(BaseModel):
    """Schema for contract deployment request."""
    contract_name: str = Field(..., description="Name of the compiled contract")
    constructor_args: Optional[List[Any]] = Field(default=[], description="Constructor arguments")
    network: Optional[str] = Field(default=settings.default_network, description="Target network")
    gas_limit: Optional[int] = Field(None, description="Gas limit for deployment")
    gas_price: Optional[int] = Field(None, description="Gas price in wei")


class ContractCallRequest(BaseModel):
    """Schema for contract function call."""
    contract_address: str = Field(..., description="Contract address")
    abi: List[Dict] = Field(..., description="Contract ABI")
    function_name: str = Field(..., description="Function name to call")
    args: Optional[List[Any]] = Field(default=[], description="Function arguments")
    network: Optional[str] = Field(default=settings.default_network, description="Network")
    from_address: Optional[str] = Field(None, description="From address for view functions")


class ContractTransactionRequest(BaseModel):
    """Schema for contract transaction."""
    contract_address: str = Field(..., description="Contract address")
    abi: List[Dict] = Field(..., description="Contract ABI")
    function_name: str = Field(..., description="Function name to call")
    args: Optional[List[Any]] = Field(default=[], description="Function arguments")
    value: Optional[int] = Field(default=0, description="ETH value to send (in wei)")
    network: Optional[str] = Field(default=settings.default_network, description="Network")
    gas_limit: Optional[int] = Field(None, description="Gas limit")
    gas_price: Optional[int] = Field(None, description="Gas price in wei")


class ContractEventsRequest(BaseModel):
    """Schema for contract events query."""
    contract_address: str = Field(..., description="Contract address")
    abi: List[Dict] = Field(..., description="Contract ABI")
    event_name: Optional[str] = Field(None, description="Specific event name")
    from_block: Optional[int] = Field(default=0, description="Starting block number")
    to_block: Optional[str] = Field(default="latest", description="Ending block")
    filters: Optional[Dict[str, Any]] = Field(default={}, description="Event filters")
    network: Optional[str] = Field(default=settings.default_network, description="Network")


class ContractVerificationRequest(BaseModel):
    """Schema for contract verification."""
    contract_address: str = Field(..., description="Contract address")
    source_code: str = Field(..., description="Source code")
    constructor_args: Optional[List[Any]] = Field(default=[], description="Constructor arguments")
    network: Optional[str] = Field(default=settings.default_network, description="Network")


class BatchCallRequest(BaseModel):
    """Schema for batch contract calls."""
    calls: List[Dict[str, Any]] = Field(..., description="List of contract calls")
    network: Optional[str] = Field(default=settings.default_network, description="Network")


# Contract Compilation Endpoints
@router.post("/compile", response_model=Dict[str, Any])
async def compile_contract(
    compile_request: ContractCompileRequest,
    db: AsyncSession = Depends(get_db)
):
    """Compile a Solidity contract."""
    try:
        compilation_result = await smart_contract_service.compile_contract(
            compile_request.contract_path,
            compile_request.contract_name
        )
        
        return {
            "status": "success",
            "result": compilation_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract compilation failed: {str(e)}"
        )


@router.post("/deploy", response_model=Dict[str, Any])
async def deploy_contract(
    deploy_request: ContractDeployRequest,
    db: AsyncSession = Depends(get_db)
):
    """Deploy a compiled contract to blockchain."""
    try:
        deployment_result = await smart_contract_service.deploy_contract(
            deploy_request.contract_name,
            deploy_request.constructor_args,
            deploy_request.network,
            deploy_request.gas_limit,
            deploy_request.gas_price
        )
        
        # Save deployment info to database
        smart_contract = SmartContract(
            name=deploy_request.contract_name,
            description=f"Deployed {deploy_request.contract_name} contract",
            contract_type=ContractType.CUSTOM,
            address=deployment_result["contract_address"],
            network=NetworkType(deploy_request.network),
            deployer_address=deployment_result["deployer_address"],
            deployment_hash=deployment_result["transaction_hash"],
            abi=deployment_result["abi"],
            bytecode=deployment_result["bytecode"],
            source_code=deployment_result["source_code"],
            deployment_block=deployment_result["block_number"],
            gas_used=deployment_result["gas_used"],
            constructor_args=deploy_request.constructor_args
        )
        
        db.add(smart_contract)
        await db.commit()
        await db.refresh(smart_contract)
        
        return {
            "status": "success",
            "deployment": deployment_result,
            "database_id": str(smart_contract.id)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract deployment failed: {str(e)}"
        )


# Contract Interaction Endpoints
@router.post("/call", response_model=Dict[str, Any])
async def call_contract_function(
    call_request: ContractCallRequest
):
    """Call a read-only contract function."""
    try:
        result = await smart_contract_service.call_contract_function(
            call_request.contract_address,
            call_request.abi,
            call_request.function_name,
            call_request.args,
            call_request.network,
            call_request.from_address
        )
        
        return {
            "status": "success",
            "result": result,
            "function_name": call_request.function_name,
            "contract_address": call_request.contract_address
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract function call failed: {str(e)}"
        )


@router.post("/transaction", response_model=Dict[str, Any])
async def send_contract_transaction(
    transaction_request: ContractTransactionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a transaction to a contract function."""
    try:
        transaction_result = await smart_contract_service.send_contract_transaction(
            transaction_request.contract_address,
            transaction_request.abi,
            transaction_request.function_name,
            transaction_request.args,
            transaction_request.value,
            transaction_request.network,
            transaction_request.gas_limit,
            transaction_request.gas_price
        )
        
        return {
            "status": "success",
            "transaction": transaction_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract transaction failed: {str(e)}"
        )


@router.post("/events", response_model=Dict[str, Any])
async def get_contract_events(
    events_request: ContractEventsRequest
):
    """Get contract events."""
    try:
        events = await smart_contract_service.get_contract_events(
            events_request.contract_address,
            events_request.abi,
            events_request.event_name,
            events_request.from_block,
            events_request.to_block,
            events_request.filters,
            events_request.network
        )
        
        return {
            "status": "success",
            "events": events,
            "contract_address": events_request.contract_address,
            "event_count": len(events)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event retrieval failed: {str(e)}"
        )


# Contract Management Endpoints
@router.get("/contracts/{contract_id}", response_model=Dict[str, Any])
async def get_contract(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get contract details by ID."""
    try:
        contract = await db.get(SmartContract, contract_id)
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        # Get on-chain information
        contract_info = await smart_contract_service.get_contract_info(
            contract.address,
            contract.network.value
        )
        
        return {
            "id": str(contract.id),
            "name": contract.name,
            "description": contract.description,
            "contract_type": contract.contract_type.value,
            "address": contract.address,
            "network": contract.network.value,
            "deployer_address": contract.deployer_address,
            "deployment_hash": contract.deployment_hash,
            "deployment_block": contract.deployment_block,
            "gas_used": contract.gas_used,
            "constructor_args": contract.constructor_args,
            "abi": contract.abi,
            "created_at": contract.created_at.isoformat(),
            "on_chain_info": contract_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get contract: {str(e)}"
        )


@router.get("/contracts", response_model=Dict[str, Any])
async def list_contracts(
    network: Optional[str] = Query(None, description="Filter by network"),
    contract_type: Optional[str] = Query(None, description="Filter by contract type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List deployed contracts."""
    try:
        # Build query
        query_conditions = []
        params = {}
        
        if network:
            query_conditions.append("network = :network")
            params["network"] = network
        
        if contract_type:
            query_conditions.append("contract_type = :contract_type")
            params["contract_type"] = contract_type
        
        # Build WHERE clause
        where_clause = ""
        if query_conditions:
            where_clause = "WHERE " + " AND ".join(query_conditions)
        
        # Execute query
        offset = (page - 1) * limit
        sql = f"""
            SELECT * FROM smart_contracts 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT :limit OFFSET :offset
        """
        
        params.update({"limit": limit, "offset": offset})
        
        result = await db.execute(sql, params)
        contracts = result.fetchall()
        
        # Format results
        contract_list = []
        for contract in contracts:
            contract_list.append({
                "id": str(contract.id),
                "name": contract.name,
                "contract_type": contract.contract_type,
                "address": contract.address,
                "network": contract.network,
                "deployer_address": contract.deployer_address,
                "deployment_block": contract.deployment_block,
                "created_at": contract.created_at.isoformat()
            })
        
        return {
            "contracts": contract_list,
            "page": page,
            "limit": limit,
            "total": len(contract_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list contracts: {str(e)}"
        )


@router.post("/verify", response_model=Dict[str, Any])
async def verify_contract_source(
    verification_request: ContractVerificationRequest
):
    """Verify contract source code."""
    try:
        verification_result = await smart_contract_service.verify_contract_source(
            verification_request.contract_address,
            verification_request.source_code,
            verification_request.constructor_args,
            verification_request.network
        )
        
        return {
            "status": "success",
            "verification": verification_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract verification failed: {str(e)}"
        )


@router.get("/contracts/{contract_address}/storage/{slot}", response_model=Dict[str, Any])
async def get_contract_storage(
    contract_address: str,
    slot: int,
    network: Optional[str] = Query(default=settings.default_network, description="Network")
):
    """Get contract storage at specific slot."""
    try:
        storage_value = await smart_contract_service.get_contract_storage(
            contract_address,
            slot,
            network
        )
        
        return {
            "contract_address": contract_address,
            "storage_slot": slot,
            "storage_value": storage_value,
            "network": network
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Storage retrieval failed: {str(e)}"
        )


@router.post("/estimate-deployment-cost", response_model=Dict[str, Any])
async def estimate_deployment_cost(
    contract_name: str = Query(..., description="Contract name"),
    constructor_args: Optional[List[Any]] = Query(default=[], description="Constructor arguments"),
    network: Optional[str] = Query(default=settings.default_network, description="Network")
):
    """Estimate contract deployment cost."""
    try:
        cost_estimate = await smart_contract_service.estimate_contract_deployment_cost(
            contract_name,
            constructor_args,
            network
        )
        
        return {
            "status": "success",
            "cost_estimate": cost_estimate
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cost estimation failed: {str(e)}"
        )


@router.post("/batch-calls", response_model=Dict[str, Any])
async def batch_contract_calls(
    batch_request: BatchCallRequest
):
    """Execute multiple contract calls in batch."""
    try:
        results = await smart_contract_service.batch_contract_calls(
            batch_request.calls,
            batch_request.network
        )
        
        return {
            "status": "success",
            "results": results,
            "total_calls": len(batch_request.calls),
            "successful_calls": sum(1 for r in results if r["status"] == "success"),
            "failed_calls": sum(1 for r in results if r["status"] == "error")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch execution failed: {str(e)}"
        )


@router.get("/contracts/{contract_address}/info", response_model=Dict[str, Any])
async def get_contract_info(
    contract_address: str,
    network: Optional[str] = Query(default=settings.default_network, description="Network")
):
    """Get comprehensive contract information."""
    try:
        contract_info = await smart_contract_service.get_contract_info(
            contract_address,
            network
        )
        
        return {
            "status": "success",
            "contract_info": contract_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract info retrieval failed: {str(e)}"
        )


# Factory and Upgrade Endpoints
@router.post("/factory", response_model=Dict[str, Any])
async def create_contract_factory(
    factory_contract_name: str = Query(..., description="Factory contract name"),
    child_contract_name: str = Query(..., description="Child contract name"),
    network: Optional[str] = Query(default=settings.default_network, description="Network")
):
    """Create a contract factory."""
    try:
        factory_info = await smart_contract_service.create_contract_factory(
            factory_contract_name,
            child_contract_name,
            network
        )
        
        return {
            "status": "success",
            "factory": factory_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Factory creation failed: {str(e)}"
        )


@router.post("/upgrade", response_model=Dict[str, Any])
async def upgrade_contract(
    proxy_address: str = Query(..., description="Proxy contract address"),
    new_implementation_address: str = Query(..., description="New implementation address"),
    network: Optional[str] = Query(default=settings.default_network, description="Network")
):
    """Upgrade a proxy contract."""
    try:
        upgrade_info = await smart_contract_service.upgrade_contract(
            proxy_address,
            new_implementation_address,
            network
        )
        
        return {
            "status": "success",
            "upgrade": upgrade_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract upgrade failed: {str(e)}"
        )


# Health Check
@router.get("/health", response_model=Dict[str, Any])
async def smart_contract_health_check():
    """Smart contract service health check."""
    try:
        # Check compiler and blockchain connectivity
        network_info = {}
        for network_name in ["ethereum", "polygon", "avalanche", "bsc"]:
            try:
                w3 = smart_contract_service.blockchain_service.get_network(network_name)
                network_info[network_name] = {
                    "connected": w3.is_connected(),
                    "latest_block": w3.eth.block_number if w3.is_connected() else None
                }
            except Exception as e:
                network_info[network_name] = {
                    "connected": False,
                    "error": str(e)
                }
        
        return {
            "status": "healthy",
            "service": "smart-contract-service",
            "compiler": "solc-0.8.19",
            "networks": network_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Smart contract service unhealthy: {str(e)}"
        )