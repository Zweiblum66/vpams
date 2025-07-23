"""Token-gating routes for Web3 Integration Service"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import settings
from ..db.base import get_db
from ..models.web3_models import Web3User, Web3Wallet, TokenGateRule
from ..models.schemas import (
    TokenGateRuleCreate,
    TokenGateRuleResponse,
    TokenGateCheck,
    TokenGateCheckResult,
    TokenRequirement
)
from ..services.web3_connector import Web3ConnectorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/token-gate", tags=["token-gate"])

@router.post("/rules", response_model=TokenGateRuleResponse)
async def create_token_gate_rule(
    rule: TokenGateRuleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new token-gating rule"""
    try:
        new_rule = TokenGateRule(
            name=rule.name,
            resource_type=rule.resource_type,
            resource_id=rule.resource_id,
            chain_type=rule.chain_type,
            requirements=rule.requirements.dict(),
            is_active=rule.is_active,
            created_by=rule.created_by
        )
        
        db.add(new_rule)
        await db.commit()
        await db.refresh(new_rule)
        
        return TokenGateRuleResponse.from_orm(new_rule)
        
    except Exception as e:
        logger.error(f"Error creating token gate rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token gate rule"
        )

@router.get("/rules", response_model=List[TokenGateRuleResponse])
async def list_token_gate_rules(
    resource_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List token-gating rules"""
    try:
        stmt = select(TokenGateRule)
        
        if resource_type:
            stmt = stmt.where(TokenGateRule.resource_type == resource_type)
        if is_active is not None:
            stmt = stmt.where(TokenGateRule.is_active == is_active)
        
        result = await db.execute(stmt)
        rules = result.scalars().all()
        
        return [TokenGateRuleResponse.from_orm(rule) for rule in rules]
        
    except Exception as e:
        logger.error(f"Error listing token gate rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list token gate rules"
        )

@router.get("/rules/{rule_id}", response_model=TokenGateRuleResponse)
async def get_token_gate_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific token-gating rule"""
    try:
        rule = await db.get(TokenGateRule, rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token gate rule not found"
            )
        
        return TokenGateRuleResponse.from_orm(rule)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token gate rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get token gate rule"
        )

@router.put("/rules/{rule_id}", response_model=TokenGateRuleResponse)
async def update_token_gate_rule(
    rule_id: str,
    rule_update: TokenGateRuleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a token-gating rule"""
    try:
        rule = await db.get(TokenGateRule, rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token gate rule not found"
            )
        
        # Update fields
        rule.name = rule_update.name
        rule.resource_type = rule_update.resource_type
        rule.resource_id = rule_update.resource_id
        rule.chain_type = rule_update.chain_type
        rule.requirements = rule_update.requirements.dict()
        rule.is_active = rule_update.is_active
        
        await db.commit()
        await db.refresh(rule)
        
        return TokenGateRuleResponse.from_orm(rule)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating token gate rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update token gate rule"
        )

@router.delete("/rules/{rule_id}")
async def delete_token_gate_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a token-gating rule"""
    try:
        rule = await db.get(TokenGateRule, rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token gate rule not found"
            )
        
        await db.delete(rule)
        await db.commit()
        
        return {"message": "Token gate rule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting token gate rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete token gate rule"
        )

@router.post("/check", response_model=TokenGateCheckResult)
async def check_token_gate(
    check: TokenGateCheck,
    db: AsyncSession = Depends(get_db)
):
    """Check if user meets token-gating requirements for a resource"""
    try:
        # Get rules for the resource
        stmt = select(TokenGateRule).where(
            TokenGateRule.resource_type == check.resource_type,
            TokenGateRule.resource_id == check.resource_id,
            TokenGateRule.is_active == True
        )
        result = await db.execute(stmt)
        rules = result.scalars().all()
        
        if not rules:
            # No token gates = access granted
            return TokenGateCheckResult(
                has_access=True,
                requirements_met=[],
                requirements_failed=[]
            )
        
        # Get user's Web3 wallets
        stmt = select(Web3User).where(Web3User.user_id == check.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.wallets:
            return TokenGateCheckResult(
                has_access=False,
                requirements_met=[],
                requirements_failed=["No Web3 wallets connected"]
            )
        
        connector = Web3ConnectorService()
        requirements_met = []
        requirements_failed = []
        
        # Check each rule
        for rule in rules:
            rule_requirements = rule.requirements
            rule_met = True
            
            # Check NFT requirements
            if "nft_collections" in rule_requirements:
                for collection in rule_requirements["nft_collections"]:
                    has_nft = False
                    for wallet in user.wallets:
                        if await connector.check_nft_ownership(
                            wallet.address,
                            collection["address"],
                            collection.get("min_quantity", 1),
                            rule.chain_type
                        ):
                            has_nft = True
                            break
                    
                    if has_nft:
                        requirements_met.append(f"NFT: {collection['name']}")
                    else:
                        requirements_failed.append(f"NFT: {collection['name']}")
                        rule_met = False
            
            # Check ERC20 token requirements
            if "erc20_tokens" in rule_requirements:
                for token in rule_requirements["erc20_tokens"]:
                    has_balance = False
                    for wallet in user.wallets:
                        balance = await connector.get_token_balance(
                            wallet.address,
                            token["address"],
                            rule.chain_type
                        )
                        if balance >= token["min_balance"]:
                            has_balance = True
                            break
                    
                    if has_balance:
                        requirements_met.append(f"Token: {token['name']}")
                    else:
                        requirements_failed.append(f"Token: {token['name']}")
                        rule_met = False
            
            # Check native token (ETH, MATIC, etc.) requirements
            if "native_token_balance" in rule_requirements:
                min_balance = rule_requirements["native_token_balance"]
                has_balance = False
                for wallet in user.wallets:
                    if wallet.chain_type == rule.chain_type:
                        balance = await connector.get_native_balance(wallet.address)
                        if balance >= min_balance:
                            has_balance = True
                            break
                
                if has_balance:
                    requirements_met.append(f"Native token: {min_balance}")
                else:
                    requirements_failed.append(f"Native token: {min_balance}")
                    rule_met = False
            
            # Check if user has any NFT from specific collections
            if "any_nft" in rule_requirements:
                collections = rule_requirements["any_nft"]
                has_any = False
                for wallet in user.wallets:
                    for collection in collections:
                        if await connector.check_nft_ownership(
                            wallet.address,
                            collection["address"],
                            1,
                            rule.chain_type
                        ):
                            has_any = True
                            break
                    if has_any:
                        break
                
                if has_any:
                    requirements_met.append("Any NFT from specified collections")
                else:
                    requirements_failed.append("Any NFT from specified collections")
                    rule_met = False
            
            if not rule_met:
                break
        
        has_access = len(requirements_failed) == 0
        
        return TokenGateCheckResult(
            has_access=has_access,
            requirements_met=requirements_met,
            requirements_failed=requirements_failed
        )
        
    except Exception as e:
        logger.error(f"Error checking token gate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check token gate"
        )

@router.post("/bulk-check", response_model=Dict[str, TokenGateCheckResult])
async def bulk_check_token_gates(
    checks: List[TokenGateCheck],
    db: AsyncSession = Depends(get_db)
):
    """Bulk check token-gating requirements for multiple resources"""
    try:
        results = {}
        
        for check in checks:
            key = f"{check.resource_type}:{check.resource_id}:{check.user_id}"
            result = await check_token_gate(check, db)
            results[key] = result
        
        return results
        
    except Exception as e:
        logger.error(f"Error bulk checking token gates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk check token gates"
        )

@router.post("/sync-tokens/{user_id}")
async def sync_user_tokens(
    user_id: str,
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Sync user's token holdings across all wallets"""
    try:
        # Get user
        stmt = select(Web3User).where(Web3User.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # TODO: Implement token sync logic
        # This would query blockchain for user's token holdings
        # and update local cache for faster access
        
        logger.info(f"Syncing tokens for user {user_id}")
        
        return {"message": f"Token sync initiated for {len(user.wallets)} wallets"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing user tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync user tokens"
        )