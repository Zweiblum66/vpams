"""
Support ticket API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime
import logging
import secrets

from src.db.base import get_db
from src.db.models import (
    SupportTicket, TicketComment,
    TicketStatus, TicketPriority
)
from src.models.schemas import (
    TicketCreate, TicketResponse, TicketUpdate,
    CommentCreate, CommentResponse,
    KnowledgeBaseArticle, KnowledgeSearchResult
)
from src.core.auth import get_current_user
from src.services.support_service import SupportService
from src.services.knowledge_base import KnowledgeBaseService
from src.services.email import EmailService

router = APIRouter()
logger = logging.getLogger(__name__)
support_service = SupportService()
kb_service = KnowledgeBaseService()
email_service = EmailService()


def generate_ticket_number() -> str:
    """Generate unique ticket number"""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"TKT-{timestamp}-{random_part}"


@router.get("/tickets", response_model=List[TicketResponse])
async def list_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    search: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List support tickets for organization"""
    query = select(SupportTicket).where(
        SupportTicket.organization_id == current_user.organization_id
    )
    
    # Apply filters
    if status:
        query = query.where(SupportTicket.status == status)
    
    if priority:
        query = query.where(SupportTicket.priority == priority)
    
    if search:
        query = query.where(
            or_(
                SupportTicket.subject.ilike(f"%{search}%"),
                SupportTicket.description.ilike(f"%{search}%"),
                SupportTicket.ticket_number.ilike(f"%{search}%")
            )
        )
    
    # Order by created date desc
    query = query.order_by(SupportTicket.created_at.desc())
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    # Get comment counts
    ticket_ids = [ticket.id for ticket in tickets]
    comment_counts = await db.execute(
        select(
            TicketComment.ticket_id,
            func.count(TicketComment.id).label("count")
        ).where(
            TicketComment.ticket_id.in_(ticket_ids)
        ).group_by(TicketComment.ticket_id)
    )
    comment_map = {row[0]: row[1] for row in comment_counts}
    
    # Build response
    response = []
    for ticket in tickets:
        response.append(TicketResponse(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            subject=ticket.subject,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            category=ticket.category,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            resolved_at=ticket.resolved_at,
            comment_count=comment_map.get(ticket.id, 0),
            created_by=ticket.created_by,
            assigned_to=ticket.assigned_to
        ))
    
    return response


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket: TicketCreate,
    attachments: Optional[List[UploadFile]] = File(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new support ticket"""
    # Generate ticket number
    ticket_number = generate_ticket_number()
    
    # Create ticket
    new_ticket = SupportTicket(
        organization_id=current_user.organization_id,
        ticket_number=ticket_number,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        category=ticket.category,
        created_by=current_user.id
    )
    
    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)
    
    # Handle attachments
    if attachments:
        for attachment in attachments:
            # TODO: Upload to storage service
            pass
    
    # Send confirmation email
    await email_service.send_ticket_confirmation(
        to_email=current_user.email,
        ticket_number=ticket_number,
        subject=ticket.subject
    )
    
    # Create notification for support team
    await support_service.notify_support_team(
        ticket_id=str(new_ticket.id),
        priority=ticket.priority
    )
    
    logger.info(f"Ticket {ticket_number} created by user {current_user.id}")
    
    return TicketResponse(
        id=new_ticket.id,
        ticket_number=new_ticket.ticket_number,
        subject=new_ticket.subject,
        description=new_ticket.description,
        status=new_ticket.status,
        priority=new_ticket.priority,
        category=new_ticket.category,
        created_at=new_ticket.created_at,
        updated_at=new_ticket.updated_at,
        resolved_at=new_ticket.resolved_at,
        comment_count=0,
        created_by=new_ticket.created_by,
        assigned_to=new_ticket.assigned_to
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get ticket details"""
    ticket = await db.execute(
        select(SupportTicket).where(
            and_(
                SupportTicket.id == ticket_id,
                SupportTicket.organization_id == current_user.organization_id
            )
        )
    )
    ticket = ticket.scalar()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Get comment count
    comment_count = await db.execute(
        select(func.count()).select_from(TicketComment).where(
            TicketComment.ticket_id == ticket.id
        )
    )
    comment_count = comment_count.scalar()
    
    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        comment_count=comment_count,
        created_by=ticket.created_by,
        assigned_to=ticket.assigned_to
    )


@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    update: TicketUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update ticket (status, priority)"""
    ticket = await db.execute(
        select(SupportTicket).where(
            and_(
                SupportTicket.id == ticket_id,
                SupportTicket.organization_id == current_user.organization_id
            )
        )
    )
    ticket = ticket.scalar()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Update fields
    if update.status is not None:
        ticket.status = update.status
        if update.status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.utcnow()
    
    if update.priority is not None:
        ticket.priority = update.priority
    
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ticket)
    
    logger.info(f"Ticket {ticket.ticket_number} updated by user {current_user.id}")
    
    # Get comment count for response
    comment_count = await db.execute(
        select(func.count()).select_from(TicketComment).where(
            TicketComment.ticket_id == ticket.id
        )
    )
    comment_count = comment_count.scalar()
    
    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        comment_count=comment_count,
        created_by=ticket.created_by,
        assigned_to=ticket.assigned_to
    )


@router.get("/tickets/{ticket_id}/comments", response_model=List[CommentResponse])
async def list_ticket_comments(
    ticket_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List comments for a ticket"""
    # Verify ticket belongs to organization
    ticket = await db.execute(
        select(SupportTicket.id).where(
            and_(
                SupportTicket.id == ticket_id,
                SupportTicket.organization_id == current_user.organization_id
            )
        )
    )
    if not ticket.scalar():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Get comments
    comments = await db.execute(
        select(TicketComment).where(
            and_(
                TicketComment.ticket_id == ticket_id,
                TicketComment.is_internal == False  # Don't show internal comments
            )
        ).order_by(TicketComment.created_at)
    )
    comments = comments.scalars().all()
    
    return [
        CommentResponse(
            id=comment.id,
            comment=comment.comment,
            created_by=comment.created_by,
            created_at=comment.created_at,
            is_internal=comment.is_internal
        )
        for comment in comments
    ]


@router.post("/tickets/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_ticket_comment(
    ticket_id: str,
    comment: CommentCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add comment to ticket"""
    # Verify ticket belongs to organization
    ticket = await db.execute(
        select(SupportTicket).where(
            and_(
                SupportTicket.id == ticket_id,
                SupportTicket.organization_id == current_user.organization_id
            )
        )
    )
    ticket = ticket.scalar()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Create comment
    new_comment = TicketComment(
        ticket_id=ticket_id,
        comment=comment.comment,
        created_by=current_user.id,
        is_internal=False
    )
    
    db.add(new_comment)
    
    # Update ticket updated_at
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(new_comment)
    
    # Notify support team
    await support_service.notify_new_comment(
        ticket_id=ticket_id,
        comment_id=str(new_comment.id),
        ticket_number=ticket.ticket_number
    )
    
    logger.info(f"Comment added to ticket {ticket.ticket_number} by user {current_user.id}")
    
    return CommentResponse(
        id=new_comment.id,
        comment=new_comment.comment,
        created_by=new_comment.created_by,
        created_at=new_comment.created_at,
        is_internal=new_comment.is_internal
    )


@router.get("/kb/search", response_model=List[KnowledgeSearchResult])
async def search_knowledge_base(
    q: str = Query(..., min_length=3),
    category: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50)
):
    """Search knowledge base articles"""
    results = await kb_service.search(
        query=q,
        category=category,
        limit=limit
    )
    
    return [
        KnowledgeSearchResult(
            id=article["id"],
            title=article["title"],
            summary=article["summary"],
            category=article["category"],
            url=article["url"],
            relevance_score=article["score"]
        )
        for article in results
    ]


@router.get("/kb/categories", response_model=List[str])
async def list_kb_categories():
    """List knowledge base categories"""
    return await kb_service.get_categories()


@router.get("/kb/popular", response_model=List[KnowledgeBaseArticle])
async def get_popular_articles(
    limit: int = Query(10, ge=1, le=20)
):
    """Get popular knowledge base articles"""
    articles = await kb_service.get_popular_articles(limit)
    
    return [
        KnowledgeBaseArticle(
            id=article["id"],
            title=article["title"],
            summary=article["summary"],
            category=article["category"],
            content=article["content"],
            url=article["url"],
            views=article["views"],
            helpful_count=article["helpful_count"],
            last_updated=article["last_updated"]
        )
        for article in articles
    ]