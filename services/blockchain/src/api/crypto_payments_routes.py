"""
API routes for cryptocurrency payment processing functionality.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.dependencies import get_db, get_current_user
from ..services.crypto_payments_service import (
    CryptoPaymentsService, PaymentRequest, SubscriptionPlan, EscrowDetails,
    CryptoPaymentsError, PaymentValidationError, InsufficientFundsError
)
from ..db.models import User

router = APIRouter(prefix="/api/v1/payments", tags=["crypto-payments"])

# Pydantic schemas
class PaymentRequestCreate(BaseModel):
    """Schema for creating payment requests."""
    recipient: str = Field(..., max_length=42, description="Ethereum address of recipient")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="ETH", max_length=10)
    description: str = Field(..., max_length=500)
    invoice_id: Optional[str] = Field(None, max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    expires_at: Optional[str] = None
    network: Optional[str] = None
    
    @validator("recipient")
    def validate_recipient_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


class SubscriptionPlanCreate(BaseModel):
    """Schema for creating subscription plans."""
    plan_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    description: str = Field(..., max_length=1000)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="ETH", max_length=10)
    interval: str = Field(..., description="monthly, yearly, weekly, daily")
    max_subscriptions: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    network: Optional[str] = None
    
    @validator("interval")
    def validate_interval(cls, v):
        valid_intervals = ["daily", "weekly", "monthly", "yearly"]
        if v.lower() not in valid_intervals:
            raise ValueError(f"Interval must be one of: {valid_intervals}")
        return v.lower()


class SubscriptionRequest(BaseModel):
    """Schema for subscription requests."""
    plan_id: str = Field(..., max_length=50)
    network: Optional[str] = None


class InvoiceCreate(BaseModel):
    """Schema for creating invoices."""
    invoice_id: str = Field(..., max_length=100)
    recipient_address: str = Field(..., max_length=42)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="ETH", max_length=10)
    description: str = Field(..., max_length=500)
    due_days: int = Field(default=30, ge=1, le=365, description="Days until due")
    network: Optional[str] = None
    
    @validator("recipient_address")
    def validate_recipient_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v.lower()


class EscrowCreate(BaseModel):
    """Schema for creating escrow transactions."""
    escrow_id: str = Field(..., max_length=100)
    seller: str = Field(..., max_length=42)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="ETH", max_length=10)
    description: str = Field(..., max_length=500)
    conditions: List[str] = Field(..., min_items=1)
    arbitrator: Optional[str] = Field(None, max_length=42)
    timeout_hours: int = Field(default=72, ge=1, le=8760)  # 1 hour to 1 year
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    network: Optional[str] = None
    
    @validator("seller", "arbitrator")
    def validate_addresses(cls, v):
        if v and (not v.startswith("0x") or len(v) != 42):
            raise ValueError("Invalid Ethereum address format")
        return v.lower() if v else v


class WithdrawRequest(BaseModel):
    """Schema for fund withdrawal requests."""
    amount: Decimal = Field(..., gt=0)
    network: Optional[str] = None


class PaymentResponse(BaseModel):
    """Standard payment response schema."""
    success: bool
    data: Dict[str, Any]
    message: str = ""


# Initialize service
crypto_payments_service = CryptoPaymentsService()


@router.post("/process", response_model=PaymentResponse)
async def process_payment(
    payment_data: PaymentRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process a cryptocurrency payment."""
    try:
        # Convert to PaymentRequest
        payment_request = PaymentRequest(
            recipient=payment_data.recipient,
            amount=payment_data.amount,
            currency=payment_data.currency,
            description=payment_data.description,
            invoice_id=payment_data.invoice_id,
            metadata=payment_data.metadata,
            expires_at=payment_data.expires_at
        )
        
        result = await crypto_payments_service.process_payment(
            payment_request=payment_request,
            sender_address=current_user.wallet_address,  # Assuming user has wallet_address
            network=payment_data.network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Payment processed successfully"
        )
        
    except PaymentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment validation failed: {str(e)}"
        )
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient funds: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {str(e)}"
        )


@router.post("/subscriptions/plans", response_model=PaymentResponse)
async def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a subscription plan."""
    try:
        # Convert to SubscriptionPlan
        subscription_plan = SubscriptionPlan(
            plan_id=plan_data.plan_id,
            name=plan_data.name,
            description=plan_data.description,
            amount=plan_data.amount,
            currency=plan_data.currency,
            interval=plan_data.interval,
            max_subscriptions=plan_data.max_subscriptions,
            metadata=plan_data.metadata
        )
        
        result = await crypto_payments_service.create_subscription_plan(
            plan=subscription_plan,
            creator_address=current_user.wallet_address,
            network=plan_data.network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Subscription plan created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription plan: {str(e)}"
        )


@router.post("/subscriptions/subscribe", response_model=PaymentResponse)
async def subscribe_to_plan(
    subscription_data: SubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Subscribe to a subscription plan."""
    try:
        result = await crypto_payments_service.subscribe_to_plan(
            plan_id=subscription_data.plan_id,
            subscriber_address=current_user.wallet_address,
            network=subscription_data.network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Successfully subscribed to plan"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subscription failed: {str(e)}"
        )


@router.delete("/subscriptions/{subscription_id}", response_model=PaymentResponse)
async def cancel_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a subscription."""
    try:
        result = await crypto_payments_service.cancel_subscription(
            subscription_id=subscription_id,
            subscriber_address=current_user.wallet_address
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Subscription cancelled successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/invoices", response_model=PaymentResponse)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an invoice."""
    try:
        due_date = datetime.utcnow() + timedelta(days=invoice_data.due_days)
        
        result = await crypto_payments_service.create_invoice(
            invoice_id=invoice_data.invoice_id,
            recipient_address=invoice_data.recipient_address,
            amount=invoice_data.amount,
            currency=invoice_data.currency,
            description=invoice_data.description,
            due_date=due_date,
            issuer_address=current_user.wallet_address,
            network=invoice_data.network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Invoice created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invoice: {str(e)}"
        )


@router.post("/invoices/{invoice_id}/pay", response_model=PaymentResponse)
async def pay_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    network: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Pay an invoice."""
    try:
        result = await crypto_payments_service.pay_invoice(
            invoice_id=invoice_id,
            payer_address=current_user.wallet_address,
            network=network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Invoice paid successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pay invoice: {str(e)}"
        )


@router.post("/escrow", response_model=PaymentResponse)
async def create_escrow(
    escrow_data: EscrowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an escrow transaction."""
    try:
        # Convert to EscrowDetails
        escrow_details = EscrowDetails(
            buyer=current_user.wallet_address,
            seller=escrow_data.seller,
            amount=escrow_data.amount,
            currency=escrow_data.currency,
            description=escrow_data.description,
            conditions=escrow_data.conditions,
            arbitrator=escrow_data.arbitrator,
            timeout_hours=escrow_data.timeout_hours,
            metadata=escrow_data.metadata
        )
        
        result = await crypto_payments_service.create_escrow(
            escrow_details=escrow_details,
            escrow_id=escrow_data.escrow_id,
            network=escrow_data.network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Escrow created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create escrow: {str(e)}"
        )


@router.post("/escrow/{escrow_id}/release", response_model=PaymentResponse)
async def release_escrow(
    escrow_id: str,
    current_user: User = Depends(get_current_user),
    network: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Release funds from escrow to seller."""
    try:
        result = await crypto_payments_service.release_escrow(
            escrow_id=escrow_id,
            releaser_address=current_user.wallet_address,
            network=network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Escrow released successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to release escrow: {str(e)}"
        )


@router.post("/escrow/{escrow_id}/refund", response_model=PaymentResponse)
async def refund_escrow(
    escrow_id: str,
    current_user: User = Depends(get_current_user),
    network: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Refund escrow to buyer."""
    try:
        result = await crypto_payments_service.refund_escrow(
            escrow_id=escrow_id,
            refunder_address=current_user.wallet_address,
            network=network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Escrow refunded successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund escrow: {str(e)}"
        )


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment_info(
    payment_id: int,
    network: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment information."""
    try:
        result = await crypto_payments_service.get_payment_info(
            payment_id=payment_id,
            network=network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Payment information retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment not found: {str(e)}"
        )


@router.get("/balance", response_model=PaymentResponse)
async def get_user_balance(
    network: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user balance."""
    try:
        result = await crypto_payments_service.get_user_balance(
            user_address=current_user.wallet_address,
            network=network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Balance retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get balance: {str(e)}"
        )


@router.post("/withdraw", response_model=PaymentResponse)
async def withdraw_funds(
    withdraw_data: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Withdraw funds from payments contract."""
    try:
        result = await crypto_payments_service.withdraw_funds(
            amount=withdraw_data.amount,
            user_address=current_user.wallet_address,
            network=withdraw_data.network
        )
        
        return PaymentResponse(
            success=True,
            data=result,
            message="Funds withdrawn successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to withdraw funds: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for crypto payments service."""
    return {
        "status": "healthy",
        "service": "crypto-payments",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }