"""
Webhook endpoints for payment processors
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json
import hmac
import hashlib
from typing import Optional

from src.db.base import get_db
from src.db.models import (
    Subscription, Payment, Invoice, Customer,
    SubscriptionStatus, PaymentStatus, InvoiceStatus
)
from src.core.config import settings
from src.services.stripe_service import StripeService
from src.services.paypal_service import PayPalService
from src.services.webhook_service import WebhookService

router = APIRouter()
logger = logging.getLogger(__name__)
stripe_service = StripeService()
paypal_service = PayPalService()
webhook_service = WebhookService()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events"""
    # Get raw body
    payload = await request.body()
    
    # Verify signature
    try:
        event = stripe_service.verify_webhook_signature(
            payload=payload,
            signature=stripe_signature,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"Stripe webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    # Handle different event types
    event_type = event["type"]
    event_data = event["data"]["object"]
    
    logger.info(f"Processing Stripe webhook: {event_type}")
    
    try:
        if event_type == "customer.subscription.created":
            await handle_stripe_subscription_created(db, event_data)
        
        elif event_type == "customer.subscription.updated":
            await handle_stripe_subscription_updated(db, event_data)
        
        elif event_type == "customer.subscription.deleted":
            await handle_stripe_subscription_deleted(db, event_data)
        
        elif event_type == "invoice.payment_succeeded":
            await handle_stripe_invoice_paid(db, event_data)
        
        elif event_type == "invoice.payment_failed":
            await handle_stripe_invoice_failed(db, event_data)
        
        elif event_type == "payment_intent.succeeded":
            await handle_stripe_payment_succeeded(db, event_data)
        
        elif event_type == "payment_intent.payment_failed":
            await handle_stripe_payment_failed(db, event_data)
        
        elif event_type == "charge.refunded":
            await handle_stripe_refund(db, event_data)
        
        elif event_type == "customer.updated":
            await handle_stripe_customer_updated(db, event_data)
        
        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )
    
    return {"status": "success"}


@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    paypal_transmission_id: str = Header(None),
    paypal_transmission_time: str = Header(None),
    paypal_transmission_sig: str = Header(None),
    paypal_cert_url: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle PayPal webhook events"""
    # Get raw body
    payload = await request.body()
    
    # Verify signature
    try:
        is_valid = await paypal_service.verify_webhook_signature(
            transmission_id=paypal_transmission_id,
            transmission_time=paypal_transmission_time,
            transmission_sig=paypal_transmission_sig,
            cert_url=paypal_cert_url,
            webhook_id=settings.PAYPAL_WEBHOOK_ID,
            payload=payload
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )
    except Exception as e:
        logger.error(f"PayPal webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    # Parse event
    event = json.loads(payload)
    event_type = event.get("event_type")
    resource = event.get("resource", {})
    
    logger.info(f"Processing PayPal webhook: {event_type}")
    
    try:
        if event_type == "BILLING.SUBSCRIPTION.CREATED":
            await handle_paypal_subscription_created(db, resource)
        
        elif event_type == "BILLING.SUBSCRIPTION.UPDATED":
            await handle_paypal_subscription_updated(db, resource)
        
        elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            await handle_paypal_subscription_cancelled(db, resource)
        
        elif event_type == "PAYMENT.SALE.COMPLETED":
            await handle_paypal_payment_completed(db, resource)
        
        elif event_type == "PAYMENT.SALE.REFUNDED":
            await handle_paypal_refund(db, resource)
        
        else:
            logger.info(f"Unhandled PayPal event type: {event_type}")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )
    
    return {"status": "success"}


# Stripe webhook handlers

async def handle_stripe_subscription_created(
    db: AsyncSession,
    subscription_data: dict
):
    """Handle Stripe subscription created"""
    stripe_sub_id = subscription_data["id"]
    
    # Find subscription by Stripe ID
    sub = await db.execute(
        select(Subscription)
        .where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = sub.scalar()
    
    if subscription:
        # Update subscription details
        subscription.status = map_stripe_status(subscription_data["status"])
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data["current_period_end"]
        )
        
        if subscription_data.get("trial_end"):
            subscription.trial_end = datetime.fromtimestamp(
                subscription_data["trial_end"]
            )


async def handle_stripe_subscription_updated(
    db: AsyncSession,
    subscription_data: dict
):
    """Handle Stripe subscription updated"""
    stripe_sub_id = subscription_data["id"]
    
    sub = await db.execute(
        select(Subscription)
        .where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = sub.scalar()
    
    if subscription:
        # Update subscription status and dates
        subscription.status = map_stripe_status(subscription_data["status"])
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data["current_period_end"]
        )
        
        # Check if cancelled
        if subscription_data.get("canceled_at"):
            subscription.canceled_at = datetime.fromtimestamp(
                subscription_data["canceled_at"]
            )
        
        # Send internal webhook
        await webhook_service.send_event(
            "subscription.updated",
            {
                "subscription_id": str(subscription.id),
                "status": subscription.status.value
            }
        )


async def handle_stripe_subscription_deleted(
    db: AsyncSession,
    subscription_data: dict
):
    """Handle Stripe subscription deleted/cancelled"""
    stripe_sub_id = subscription_data["id"]
    
    sub = await db.execute(
        select(Subscription)
        .where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = sub.scalar()
    
    if subscription:
        subscription.status = SubscriptionStatus.CANCELED
        subscription.ended_at = datetime.utcnow()
        
        # Send internal webhook
        await webhook_service.send_event(
            "subscription.cancelled",
            {
                "subscription_id": str(subscription.id)
            }
        )


async def handle_stripe_invoice_paid(
    db: AsyncSession,
    invoice_data: dict
):
    """Handle Stripe invoice paid"""
    stripe_invoice_id = invoice_data["id"]
    
    inv = await db.execute(
        select(Invoice)
        .where(Invoice.stripe_invoice_id == stripe_invoice_id)
    )
    invoice = inv.scalar()
    
    if not invoice:
        # Create invoice if it doesn't exist
        stripe_sub_id = invoice_data.get("subscription")
        if stripe_sub_id:
            sub = await db.execute(
                select(Subscription)
                .where(Subscription.stripe_subscription_id == stripe_sub_id)
            )
            subscription = sub.scalar()
            
            if subscription:
                invoice = Invoice(
                    customer_id=subscription.customer_id,
                    subscription_id=subscription.id,
                    stripe_invoice_id=stripe_invoice_id,
                    invoice_number=invoice_data["number"],
                    status=InvoiceStatus.PAID,
                    subtotal=invoice_data["subtotal"],
                    tax=invoice_data["tax"] or 0,
                    total=invoice_data["total"],
                    amount_paid=invoice_data["amount_paid"],
                    amount_due=0,
                    currency=Currency(invoice_data["currency"].upper()),
                    invoice_date=datetime.fromtimestamp(
                        invoice_data["created"]
                    ),
                    due_date=datetime.fromtimestamp(
                        invoice_data["due_date"]
                    ) if invoice_data.get("due_date") else None,
                    paid_at=datetime.fromtimestamp(
                        invoice_data["status_transitions"]["paid_at"]
                    ),
                    pdf_url=invoice_data.get("invoice_pdf")
                )
                db.add(invoice)
    else:
        # Update existing invoice
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = invoice_data["amount_paid"]
        invoice.amount_due = 0
        invoice.paid_at = datetime.fromtimestamp(
            invoice_data["status_transitions"]["paid_at"]
        )
    
    # Send internal webhook
    await webhook_service.send_event(
        "invoice.paid",
        {
            "invoice_id": str(invoice.id),
            "amount": invoice.total
        }
    )


async def handle_stripe_payment_succeeded(
    db: AsyncSession,
    payment_intent_data: dict
):
    """Handle Stripe payment succeeded"""
    stripe_payment_intent_id = payment_intent_data["id"]
    
    pay = await db.execute(
        select(Payment)
        .where(Payment.stripe_payment_intent_id == stripe_payment_intent_id)
    )
    payment = pay.scalar()
    
    if payment:
        payment.status = PaymentStatus.SUCCEEDED
        payment.stripe_charge_id = payment_intent_data.get("latest_charge")
        
        # Send internal webhook
        await webhook_service.send_event(
            "payment.succeeded",
            {
                "payment_id": str(payment.id),
                "amount": payment.amount
            }
        )


# PayPal webhook handlers

async def handle_paypal_subscription_created(
    db: AsyncSession,
    resource: dict
):
    """Handle PayPal subscription created"""
    paypal_sub_id = resource["id"]
    
    # Implementation similar to Stripe
    # Find subscription and update status
    pass


async def handle_paypal_payment_completed(
    db: AsyncSession,
    resource: dict
):
    """Handle PayPal payment completed"""
    paypal_payment_id = resource["id"]
    
    # Find payment and update status
    pay = await db.execute(
        select(Payment)
        .where(Payment.paypal_payment_id == paypal_payment_id)
    )
    payment = pay.scalar()
    
    if payment:
        payment.status = PaymentStatus.SUCCEEDED
        
        # Send internal webhook
        await webhook_service.send_event(
            "payment.succeeded",
            {
                "payment_id": str(payment.id),
                "amount": payment.amount,
                "processor": "paypal"
            }
        )


# Helper functions

def map_stripe_status(stripe_status: str) -> SubscriptionStatus:
    """Map Stripe subscription status to our status"""
    status_map = {
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "incomplete_expired": SubscriptionStatus.INCOMPLETE_EXPIRED,
        "trialing": SubscriptionStatus.TRIALING,
        "paused": SubscriptionStatus.PAUSED
    }
    return status_map.get(stripe_status, SubscriptionStatus.ACTIVE)


@router.post("/test")
async def test_webhook(
    event_type: str,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Test webhook endpoint for development"""
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test webhooks only available in debug mode"
        )
    
    # Simulate webhook event
    logger.info(f"Test webhook: {event_type}")
    logger.debug(f"Test webhook data: {data}")
    
    return {"status": "success", "event_type": event_type}


from datetime import datetime