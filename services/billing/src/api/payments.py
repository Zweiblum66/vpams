"""
Payment processing API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import uuid

from src.db.base import get_db
from src.db.models import (
    Payment, Customer, Invoice, PaymentMethod, PaymentStatus,
    PaymentMethodType, Refund, Currency
)
from src.models.schemas import (
    PaymentCreate, PaymentResponse, PaymentMethodCreate,
    PaymentMethodResponse, RefundCreate, RefundResponse,
    ChargeCreate, PaymentUpdate
)
from src.core.auth import get_current_user, require_api_key
from src.services.stripe_service import StripeService
from src.services.paypal_service import PayPalService
from src.services.notification_service import NotificationService
from src.services.webhook_service import WebhookService

router = APIRouter()
logger = logging.getLogger(__name__)
stripe_service = StripeService()
paypal_service = PayPalService()
notification_service = NotificationService()
webhook_service = WebhookService()


@router.post("/methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def add_payment_method(
    method_data: PaymentMethodCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new payment method"""
    # Get or create customer
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        customer = Customer(
            organization_id=current_user.organization_id,
            email=current_user.email,
            name=current_user.name
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
    
    # Create payment method in processor
    if method_data.type == PaymentMethodType.CARD:
        if not customer.stripe_customer_id:
            stripe_customer = await stripe_service.create_customer(
                email=customer.email,
                name=customer.name
            )
            customer.stripe_customer_id = stripe_customer.id
        
        stripe_method = await stripe_service.attach_payment_method(
            customer_id=customer.stripe_customer_id,
            payment_method_id=method_data.stripe_payment_method_id
        )
        
        # Extract card details
        card = stripe_method.card
        payment_method = PaymentMethod(
            customer_id=customer.id,
            type=PaymentMethodType.CARD,
            last4=card.last4,
            brand=card.brand,
            exp_month=card.exp_month,
            exp_year=card.exp_year,
            stripe_payment_method_id=stripe_method.id,
            is_default=method_data.set_as_default or not customer.payment_methods
        )
    
    elif method_data.type == PaymentMethodType.BANK_ACCOUNT:
        # Handle bank account
        bank_account = await stripe_service.create_bank_account(
            customer_id=customer.stripe_customer_id,
            account_number=method_data.account_number,
            routing_number=method_data.routing_number,
            account_holder_name=method_data.account_holder_name
        )
        
        payment_method = PaymentMethod(
            customer_id=customer.id,
            type=PaymentMethodType.BANK_ACCOUNT,
            bank_name=method_data.bank_name,
            account_last4=method_data.account_number[-4:],
            routing_number=method_data.routing_number,
            stripe_payment_method_id=bank_account.id,
            is_default=method_data.set_as_default or not customer.payment_methods
        )
    
    elif method_data.type == PaymentMethodType.PAYPAL:
        # Handle PayPal
        paypal_account = await paypal_service.link_account(
            customer_email=customer.email,
            return_url=method_data.return_url,
            cancel_url=method_data.cancel_url
        )
        
        payment_method = PaymentMethod(
            customer_id=customer.id,
            type=PaymentMethodType.PAYPAL,
            paypal_payment_method_id=paypal_account.id,
            is_default=method_data.set_as_default or not customer.payment_methods
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment method type: {method_data.type}"
        )
    
    # Update default if requested
    if method_data.set_as_default:
        await db.execute(
            select(PaymentMethod)
            .where(PaymentMethod.customer_id == customer.id)
            .where(PaymentMethod.is_default == True)
        )
        for pm in await db.scalars():
            pm.is_default = False
    
    db.add(payment_method)
    await db.commit()
    await db.refresh(payment_method)
    
    logger.info(f"Payment method added: {payment_method.id}")
    
    return payment_method


@router.get("/methods", response_model=List[PaymentMethodResponse])
async def list_payment_methods(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List payment methods for the current user"""
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        return []
    
    methods = await db.execute(
        select(PaymentMethod)
        .where(PaymentMethod.customer_id == customer.id)
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc())
    )
    
    return methods.scalars().all()


@router.delete("/methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_payment_method(
    method_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a payment method"""
    method = await db.execute(
        select(PaymentMethod)
        .join(Customer)
        .where(
            and_(
                PaymentMethod.id == method_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    method = method.scalar()
    
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Check if it's the default method
    if method.is_default:
        # Find another method to make default
        other_method = await db.execute(
            select(PaymentMethod)
            .where(
                and_(
                    PaymentMethod.customer_id == method.customer_id,
                    PaymentMethod.id != method.id
                )
            )
            .limit(1)
        )
        other_method = other_method.scalar()
        
        if other_method:
            other_method.is_default = True
    
    # Remove from payment processor
    if method.stripe_payment_method_id:
        await stripe_service.detach_payment_method(method.stripe_payment_method_id)
    
    await db.delete(method)
    await db.commit()
    
    logger.info(f"Payment method removed: {method_id}")


@router.post("/methods/{method_id}/default", response_model=PaymentMethodResponse)
async def set_default_payment_method(
    method_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set a payment method as default"""
    method = await db.execute(
        select(PaymentMethod)
        .join(Customer)
        .where(
            and_(
                PaymentMethod.id == method_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    method = method.scalar()
    
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Update all methods for this customer
    await db.execute(
        select(PaymentMethod)
        .where(PaymentMethod.customer_id == method.customer_id)
    )
    for pm in await db.scalars():
        pm.is_default = (pm.id == method.id)
    
    await db.commit()
    await db.refresh(method)
    
    # Update default in payment processor
    if method.stripe_payment_method_id:
        customer = await db.get(Customer, method.customer_id)
        await stripe_service.set_default_payment_method(
            customer_id=customer.stripe_customer_id,
            payment_method_id=method.stripe_payment_method_id
        )
    
    return method


@router.post("/charge", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_charge(
    charge_data: ChargeCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a one-time charge"""
    # Get customer
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Get payment method
    if charge_data.payment_method_id:
        payment_method = await db.get(PaymentMethod, charge_data.payment_method_id)
        if not payment_method or payment_method.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )
    else:
        # Use default payment method
        payment_method = await db.execute(
            select(PaymentMethod)
            .where(
                and_(
                    PaymentMethod.customer_id == customer.id,
                    PaymentMethod.is_default == True
                )
            )
        )
        payment_method = payment_method.scalar()
        
        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No payment method available"
            )
    
    # Create payment record
    payment = Payment(
        customer_id=customer.id,
        amount=int(charge_data.amount * 100),  # Convert to cents
        currency=charge_data.currency or customer.currency or Currency.USD,
        status=PaymentStatus.PENDING,
        payment_method_id=payment_method.id,
        payment_method_type=payment_method.type,
        description=charge_data.description,
        metadata=charge_data.metadata or {}
    )
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    # Process payment in background
    background_tasks.add_task(
        process_payment,
        payment_id=payment.id,
        payment_method=payment_method,
        customer=customer
    )
    
    return payment


@router.get("/history", response_model=List[PaymentResponse])
async def get_payment_history(
    status: Optional[PaymentStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment history for the current user"""
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        return []
    
    # Build query
    query = select(Payment).where(Payment.customer_id == customer.id)
    
    if status:
        query = query.where(Payment.status == status)
    
    if start_date:
        query = query.where(Payment.created_at >= start_date)
    
    if end_date:
        query = query.where(Payment.created_at <= end_date)
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(Payment.created_at.desc())
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return payments


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment details"""
    payment = await db.execute(
        select(Payment)
        .join(Customer)
        .where(
            and_(
                Payment.id == payment_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    payment = payment.scalar()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return payment


@router.post("/{payment_id}/refund", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def refund_payment(
    payment_id: str,
    refund_data: RefundCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refund a payment"""
    payment = await db.execute(
        select(Payment)
        .join(Customer)
        .where(
            and_(
                Payment.id == payment_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    payment = payment.scalar()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status != PaymentStatus.SUCCEEDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only refund successful payments"
        )
    
    # Check refund amount
    refund_amount = refund_data.amount * 100 if refund_data.amount else payment.amount
    available_to_refund = payment.amount - payment.refunded_amount
    
    if refund_amount > available_to_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot refund more than {available_to_refund / 100:.2f}"
        )
    
    # Create refund record
    refund = Refund(
        payment_id=payment.id,
        amount=refund_amount,
        currency=payment.currency,
        status=PaymentStatus.PENDING,
        reason=refund_data.reason
    )
    
    db.add(refund)
    await db.commit()
    await db.refresh(refund)
    
    # Process refund in background
    background_tasks.add_task(
        process_refund,
        refund_id=refund.id,
        payment=payment
    )
    
    return refund


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: str,
    update_data: PaymentUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update payment metadata or description"""
    payment = await db.execute(
        select(Payment)
        .join(Customer)
        .where(
            and_(
                Payment.id == payment_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    payment = payment.scalar()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if update_data.description is not None:
        payment.description = update_data.description
    
    if update_data.metadata:
        payment.metadata.update(update_data.metadata)
    
    await db.commit()
    await db.refresh(payment)
    
    return payment


# Background tasks
async def process_payment(
    payment_id: uuid.UUID,
    payment_method: PaymentMethod,
    customer: Customer
):
    """Process payment in background"""
    async with AsyncSession() as db:
        payment = await db.get(Payment, payment_id)
        
        try:
            if payment_method.type == PaymentMethodType.CARD:
                # Process with Stripe
                intent = await stripe_service.create_payment_intent(
                    amount=payment.amount,
                    currency=payment.currency.value,
                    customer_id=customer.stripe_customer_id,
                    payment_method_id=payment_method.stripe_payment_method_id,
                    description=payment.description,
                    metadata=payment.metadata
                )
                
                payment.stripe_payment_intent_id = intent.id
                
                # Confirm payment
                confirmed = await stripe_service.confirm_payment_intent(intent.id)
                
                if confirmed.status == "succeeded":
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.stripe_charge_id = confirmed.latest_charge
                else:
                    payment.status = PaymentStatus.FAILED
                    payment.failure_code = confirmed.last_payment_error.code
                    payment.failure_message = confirmed.last_payment_error.message
            
            elif payment_method.type == PaymentMethodType.PAYPAL:
                # Process with PayPal
                paypal_payment = await paypal_service.create_payment(
                    amount=payment.amount / 100,  # Convert from cents
                    currency=payment.currency.value,
                    description=payment.description
                )
                
                payment.paypal_payment_id = paypal_payment.id
                payment.status = PaymentStatus.SUCCEEDED
            
            await db.commit()
            
            # Send notifications
            if payment.status == PaymentStatus.SUCCEEDED:
                await notification_service.send_payment_success(payment)
                await webhook_service.send_event(
                    "payment.succeeded",
                    {
                        "payment_id": str(payment.id),
                        "amount": payment.amount,
                        "currency": payment.currency.value
                    }
                )
            else:
                await notification_service.send_payment_failed(payment)
                await webhook_service.send_event(
                    "payment.failed",
                    {
                        "payment_id": str(payment.id),
                        "failure_code": payment.failure_code,
                        "failure_message": payment.failure_message
                    }
                )
                
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            payment.status = PaymentStatus.FAILED
            payment.failure_message = str(e)
            await db.commit()


async def process_refund(
    refund_id: uuid.UUID,
    payment: Payment
):
    """Process refund in background"""
    async with AsyncSession() as db:
        refund = await db.get(Refund, refund_id)
        
        try:
            if payment.stripe_charge_id:
                # Process with Stripe
                stripe_refund = await stripe_service.create_refund(
                    charge_id=payment.stripe_charge_id,
                    amount=refund.amount,
                    reason=refund.reason
                )
                
                refund.stripe_refund_id = stripe_refund.id
                refund.status = PaymentStatus.SUCCEEDED
                
            elif payment.paypal_payment_id:
                # Process with PayPal
                paypal_refund = await paypal_service.create_refund(
                    payment_id=payment.paypal_payment_id,
                    amount=refund.amount / 100,  # Convert from cents
                    reason=refund.reason
                )
                
                refund.paypal_refund_id = paypal_refund.id
                refund.status = PaymentStatus.SUCCEEDED
            
            # Update payment refunded amount
            payment.refunded_amount += refund.amount
            if payment.refunded_amount == payment.amount:
                payment.status = PaymentStatus.REFUNDED
            else:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED
            
            await db.commit()
            
            # Send notifications
            await notification_service.send_refund_processed(refund)
            await webhook_service.send_event(
                "payment.refunded",
                {
                    "payment_id": str(payment.id),
                    "refund_id": str(refund.id),
                    "amount": refund.amount,
                    "reason": refund.reason
                }
            )
            
        except Exception as e:
            logger.error(f"Refund processing failed: {e}")
            refund.status = PaymentStatus.FAILED
            await db.commit()


@router.post("/retry/{payment_id}", response_model=PaymentResponse)
async def retry_payment(
    payment_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed payment"""
    payment = await db.execute(
        select(Payment)
        .join(Customer)
        .where(
            and_(
                Payment.id == payment_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    payment = payment.scalar()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status != PaymentStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed payments"
        )
    
    # Reset payment status
    payment.status = PaymentStatus.PENDING
    payment.failure_code = None
    payment.failure_message = None
    
    await db.commit()
    
    # Get payment method and customer
    payment_method = await db.get(PaymentMethod, payment.payment_method_id)
    customer = await db.get(Customer, payment.customer_id)
    
    # Process payment in background
    background_tasks.add_task(
        process_payment,
        payment_id=payment.id,
        payment_method=payment_method,
        customer=customer
    )
    
    return payment