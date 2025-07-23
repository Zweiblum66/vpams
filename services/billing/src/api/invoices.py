"""
Invoice management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta, date
import logging
import io

from src.db.base import get_db
from src.db.models import (
    Invoice, Customer, Subscription, InvoiceStatus,
    InvoiceLineItem, Payment, Currency
)
from src.models.schemas import (
    InvoiceResponse, InvoiceCreate, InvoiceUpdate,
    InvoiceLineItemCreate, InvoiceSend
)
from src.core.auth import get_current_user, require_api_key
from src.services.pdf_service import PDFService
from src.services.email_service import EmailService
from src.services.invoice_service import InvoiceService
from src.services.webhook_service import WebhookService

router = APIRouter()
logger = logging.getLogger(__name__)
pdf_service = PDFService()
email_service = EmailService()
invoice_service = InvoiceService()
webhook_service = WebhookService()


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    status: Optional[InvoiceStatus] = None,
    subscription_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List invoices for the current user"""
    # Get customer
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        return []
    
    # Build query
    query = select(Invoice).where(Invoice.customer_id == customer.id)
    
    if status:
        query = query.where(Invoice.status == status)
    
    if subscription_id:
        query = query.where(Invoice.subscription_id == subscription_id)
    
    if start_date:
        query = query.where(Invoice.invoice_date >= start_date)
    
    if end_date:
        query = query.where(Invoice.invoice_date <= end_date)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(Invoice.created_at.desc())
    
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    # Add pagination headers
    headers = {
        "X-Total-Count": str(total),
        "X-Page": str(page),
        "X-Limit": str(limit)
    }
    
    return invoices


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice details"""
    invoice = await db.execute(
        select(Invoice)
        .join(Customer)
        .where(
            and_(
                Invoice.id == invoice_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    invoice = invoice.scalar()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Load line items
    line_items = await db.execute(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice.id)
        .order_by(InvoiceLineItem.id)
    )
    invoice.line_items = line_items.scalars().all()
    
    return invoice


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download invoice as PDF"""
    invoice = await db.execute(
        select(Invoice)
        .join(Customer)
        .where(
            and_(
                Invoice.id == invoice_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    invoice = invoice.scalar()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Load related data
    customer = await db.get(Customer, invoice.customer_id)
    line_items = await db.execute(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice.id)
        .order_by(InvoiceLineItem.id)
    )
    invoice.line_items = line_items.scalars().all()
    
    # Generate PDF
    pdf_buffer = await pdf_service.generate_invoice_pdf(
        invoice=invoice,
        customer=customer
    )
    
    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(pdf_buffer),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"
        }
    )


@router.post("/{invoice_id}/send", status_code=status.HTTP_204_NO_CONTENT)
async def send_invoice_email(
    invoice_id: str,
    send_data: InvoiceSend,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send invoice via email"""
    invoice = await db.execute(
        select(Invoice)
        .join(Customer)
        .where(
            and_(
                Invoice.id == invoice_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    invoice = invoice.scalar()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status == InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send draft invoices"
        )
    
    # Load related data
    customer = await db.get(Customer, invoice.customer_id)
    line_items = await db.execute(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice.id)
        .order_by(InvoiceLineItem.id)
    )
    invoice.line_items = line_items.scalars().all()
    
    # Generate PDF
    pdf_buffer = await pdf_service.generate_invoice_pdf(
        invoice=invoice,
        customer=customer
    )
    
    # Send email
    recipients = send_data.recipients or [customer.email]
    
    await email_service.send_invoice(
        invoice=invoice,
        recipients=recipients,
        cc=send_data.cc,
        subject=send_data.subject or f"Invoice {invoice.invoice_number}",
        message=send_data.message,
        pdf_attachment=pdf_buffer
    )
    
    # Update sent timestamp
    invoice.metadata["last_sent_at"] = datetime.utcnow().isoformat()
    invoice.metadata["sent_to"] = recipients
    
    await db.commit()
    
    logger.info(f"Invoice {invoice.id} sent to {recipients}")


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    update_data: InvoiceUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update draft invoice"""
    invoice = await db.execute(
        select(Invoice)
        .join(Customer)
        .where(
            and_(
                Invoice.id == invoice_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    invoice = invoice.scalar()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft invoices"
        )
    
    # Update fields
    if update_data.due_date:
        invoice.due_date = update_data.due_date
    
    if update_data.notes:
        invoice.notes = update_data.notes
    
    if update_data.metadata:
        invoice.metadata.update(update_data.metadata)
    
    invoice.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(invoice)
    
    return invoice


@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
async def void_invoice(
    invoice_id: str,
    reason: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Void an invoice"""
    invoice = await db.execute(
        select(Invoice)
        .join(Customer)
        .where(
            and_(
                Invoice.id == invoice_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    invoice = invoice.scalar()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot void paid invoices"
        )
    
    if invoice.status == InvoiceStatus.VOID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice already voided"
        )
    
    # Void invoice
    invoice.status = InvoiceStatus.VOID
    invoice.metadata["voided_at"] = datetime.utcnow().isoformat()
    invoice.metadata["voided_by"] = current_user.id
    if reason:
        invoice.metadata["void_reason"] = reason
    
    await db.commit()
    await db.refresh(invoice)
    
    # Send webhook
    await webhook_service.send_event(
        "invoice.voided",
        {
            "invoice_id": str(invoice.id),
            "reason": reason
        }
    )
    
    logger.info(f"Invoice {invoice.id} voided")
    
    return invoice


@router.post("/{invoice_id}/finalize", response_model=InvoiceResponse)
async def finalize_invoice(
    invoice_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Finalize a draft invoice"""
    invoice = await db.execute(
        select(Invoice)
        .join(Customer)
        .where(
            and_(
                Invoice.id == invoice_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    invoice = invoice.scalar()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only finalize draft invoices"
        )
    
    # Generate invoice number if not set
    if not invoice.invoice_number:
        invoice.invoice_number = await invoice_service.generate_invoice_number(db)
    
    # Update status
    invoice.status = InvoiceStatus.OPEN
    invoice.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(invoice)
    
    # Send webhook
    await webhook_service.send_event(
        "invoice.finalized",
        {
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "amount_due": invoice.amount_due
        }
    )
    
    logger.info(f"Invoice {invoice.id} finalized")
    
    return invoice


@router.post("/{invoice_id}/pay", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: str,
    payment_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark invoice as paid"""
    invoice = await db.execute(
        select(Invoice)
        .join(Customer)
        .where(
            and_(
                Invoice.id == invoice_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    invoice = invoice.scalar()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice already paid"
        )
    
    if invoice.status not in [InvoiceStatus.OPEN, InvoiceStatus.DRAFT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark this invoice as paid"
        )
    
    # Update invoice
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = datetime.utcnow()
    invoice.amount_paid = invoice.total
    invoice.amount_due = 0
    
    if payment_id:
        # Link to payment
        payment = await db.get(Payment, payment_id)
        if payment and payment.customer_id == invoice.customer_id:
            payment.invoice_id = invoice.id
    
    await db.commit()
    await db.refresh(invoice)
    
    # Send webhook
    await webhook_service.send_event(
        "invoice.paid",
        {
            "invoice_id": str(invoice.id),
            "paid_at": invoice.paid_at.isoformat(),
            "payment_id": payment_id
        }
    )
    
    logger.info(f"Invoice {invoice.id} marked as paid")
    
    return invoice


@router.get("/upcoming", response_model=List[InvoiceResponse])
async def get_upcoming_invoices(
    days_ahead: int = Query(30, ge=1, le=90),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming/predicted invoices"""
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        return []
    
    # Get active subscriptions
    subscriptions = await db.execute(
        select(Subscription)
        .where(
            and_(
                Subscription.customer_id == customer.id,
                Subscription.status.in_(["active", "trialing"])
            )
        )
    )
    subscriptions = subscriptions.scalars().all()
    
    upcoming_invoices = []
    end_date = datetime.utcnow() + timedelta(days=days_ahead)
    
    for subscription in subscriptions:
        # Calculate next billing dates
        current_date = subscription.current_period_end
        
        while current_date <= end_date:
            # Create preview invoice
            preview = await invoice_service.create_preview_invoice(
                subscription=subscription,
                billing_date=current_date
            )
            upcoming_invoices.append(preview)
            
            # Move to next period
            current_date = current_date + timedelta(days=30)  # Simplified - should use plan interval
    
    return upcoming_invoices


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a manual invoice"""
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
    
    # Create invoice
    invoice = Invoice(
        customer_id=customer.id,
        status=InvoiceStatus.DRAFT,
        invoice_date=invoice_data.invoice_date or datetime.utcnow(),
        due_date=invoice_data.due_date or datetime.utcnow() + timedelta(days=30),
        currency=invoice_data.currency or customer.currency or Currency.USD,
        notes=invoice_data.notes,
        metadata=invoice_data.metadata or {},
        subtotal=0,
        tax=0,
        total=0,
        amount_due=0
    )
    
    db.add(invoice)
    await db.flush()  # Get invoice ID
    
    # Add line items
    subtotal = 0
    for item_data in invoice_data.line_items:
        amount = int(item_data.quantity * item_data.unit_price * 100)  # Convert to cents
        
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=int(item_data.unit_price * 100),
            amount=amount,
            type=item_data.type or "custom",
            metadata=item_data.metadata or {}
        )
        
        db.add(line_item)
        subtotal += amount
    
    # Calculate totals
    invoice.subtotal = subtotal
    invoice.tax = int(subtotal * (invoice_data.tax_rate or 0) / 100)
    invoice.total = invoice.subtotal + invoice.tax
    invoice.amount_due = invoice.total
    
    await db.commit()
    await db.refresh(invoice)
    
    # Send webhook
    await webhook_service.send_event(
        "invoice.created",
        {
            "invoice_id": str(invoice.id),
            "customer_id": str(customer.id),
            "total": invoice.total,
            "currency": invoice.currency.value
        }
    )
    
    logger.info(f"Manual invoice created: {invoice.id}")
    
    return invoice


@router.get("/statistics", response_model=dict)
async def get_invoice_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoice statistics"""
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        return {
            "total_invoices": 0,
            "paid_invoices": 0,
            "open_invoices": 0,
            "overdue_invoices": 0,
            "total_amount": 0,
            "paid_amount": 0,
            "outstanding_amount": 0
        }
    
    # Build base query
    query = select(Invoice).where(Invoice.customer_id == customer.id)
    
    if start_date:
        query = query.where(Invoice.invoice_date >= start_date)
    
    if end_date:
        query = query.where(Invoice.invoice_date <= end_date)
    
    # Get all invoices
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    # Calculate statistics
    total_invoices = len(invoices)
    paid_invoices = sum(1 for inv in invoices if inv.status == InvoiceStatus.PAID)
    open_invoices = sum(1 for inv in invoices if inv.status == InvoiceStatus.OPEN)
    overdue_invoices = sum(
        1 for inv in invoices 
        if inv.status == InvoiceStatus.OPEN and inv.due_date < datetime.utcnow()
    )
    
    total_amount = sum(inv.total for inv in invoices)
    paid_amount = sum(inv.amount_paid for inv in invoices)
    outstanding_amount = sum(inv.amount_due for inv in invoices)
    
    return {
        "total_invoices": total_invoices,
        "paid_invoices": paid_invoices,
        "open_invoices": open_invoices,
        "overdue_invoices": overdue_invoices,
        "total_amount": total_amount / 100,  # Convert from cents
        "paid_amount": paid_amount / 100,
        "outstanding_amount": outstanding_amount / 100,
        "average_payment_time_days": await calculate_average_payment_time(invoices)
    }


async def calculate_average_payment_time(invoices: List[Invoice]) -> float:
    """Calculate average time to payment"""
    payment_times = []
    
    for invoice in invoices:
        if invoice.status == InvoiceStatus.PAID and invoice.paid_at:
            days = (invoice.paid_at - invoice.invoice_date).days
            payment_times.append(days)
    
    if payment_times:
        return sum(payment_times) / len(payment_times)
    
    return 0.0