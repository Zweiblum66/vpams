"""Data Request API Endpoints (GDPR Rights)"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from datetime import datetime, timedelta

from ...db.models import DataRequest, DataRequestType, DataRequestStatus
from ...models.schemas import (
    DataRequestCreate, DataRequestResponse, DataRequestVerify,
    DataRequestCancel, DataRequestProgress, DataExportRequest,
    DataExportResponse, DataDeletionRequest, DataDeletionResponse
)
from ...services.data_export_service import DataExportService
from ...services.data_deletion_service import DataDeletionService
from ...services.audit_service import AuditService
from ...core.security import generate_request_id, generate_verification_token
from ...core.config import settings
from ..dependencies import get_db, get_current_user, get_client_ip

router = APIRouter()


@router.post("/", response_model=DataRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_data_request(
    request_data: DataRequestCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new GDPR data request"""
    # Validate user can only create requests for themselves (unless admin)
    if str(request_data.user_id) != current_user["user_id"] and \
       "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create data request for another user"
        )
    
    # Check for existing pending requests of same type
    result = await db.execute(
        select(DataRequest).where(
            and_(
                DataRequest.user_id == request_data.user_id,
                DataRequest.request_type == request_data.request_type,
                DataRequest.status.in_([DataRequestStatus.PENDING, DataRequestStatus.IN_PROGRESS])
            )
        )
    )
    existing_request = result.scalar_one_or_none()
    
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {request_data.request_type.value} request is already pending"
        )
    
    # Create request
    data_request = DataRequest(
        request_id=generate_request_id(),
        user_id=request_data.user_id,
        request_type=request_data.request_type,
        requested_by=request_data.requested_by,
        request_reason=request_data.request_reason,
        notification_email=request_data.notification_email,
        request_data=request_data.request_data,
        export_format=request_data.export_format.value if request_data.export_format else None
    )
    
    # Set verification requirements
    if request_data.request_type in [DataRequestType.ERASURE, DataRequestType.PORTABILITY]:
        data_request.verification_token = generate_verification_token()
        data_request.verification_expires = datetime.utcnow() + timedelta(hours=24)
    
    db.add(data_request)
    await db.commit()
    await db.refresh(data_request)
    
    # Log audit event
    audit_service = AuditService(db)
    await audit_service.log_data_request(
        user_id=data_request.user_id,
        request_type=data_request.request_type.value,
        request_id=data_request.request_id,
        actor_id=UUID(current_user["user_id"]),
        actor_ip=get_client_ip(request)
    )
    
    # Process request in background if no verification needed
    if not data_request.verification_token:
        if data_request.request_type == DataRequestType.ACCESS:
            background_tasks.add_task(
                process_data_export_request,
                data_request.request_id,
                request_data,
                db
            )
    
    return DataRequestResponse(
        id=data_request.id,
        request_id=data_request.request_id,
        user_id=data_request.user_id,
        request_type=data_request.request_type,
        notification_email=data_request.notification_email,
        request_reason=data_request.request_reason,
        status=data_request.status,
        requested_at=data_request.requested_at,
        requested_by=data_request.requested_by,
        processed_at=data_request.processed_at,
        export_format=data_request.export_format,
        export_size_bytes=data_request.export_size_bytes,
        verification_required=bool(data_request.verification_token),
        verified=data_request.verified,
        error_message=data_request.error_message
    )


@router.post("/{request_id}/verify", response_model=DataRequestResponse)
async def verify_data_request(
    request_id: str,
    verification: DataRequestVerify,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Verify a data request with token"""
    # Get request
    result = await db.execute(
        select(DataRequest).where(DataRequest.request_id == request_id)
    )
    data_request = result.scalar_one_or_none()
    
    if not data_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data request not found"
        )
    
    if data_request.verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request already verified"
        )
    
    if not data_request.verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request does not require verification"
        )
    
    # Check token
    if data_request.verification_token != verification.verification_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification token"
        )
    
    # Check expiration
    if data_request.verification_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Verification token has expired"
        )
    
    # Mark as verified
    data_request.verified = True
    data_request.verified_at = datetime.utcnow()
    await db.commit()
    
    # Process request in background
    if data_request.request_type == DataRequestType.ERASURE:
        background_tasks.add_task(
            process_deletion_request,
            data_request.request_id,
            db
        )
    elif data_request.request_type in [DataRequestType.ACCESS, DataRequestType.PORTABILITY]:
        background_tasks.add_task(
            process_data_export_request,
            data_request.request_id,
            None,
            db
        )
    
    return DataRequestResponse(
        id=data_request.id,
        request_id=data_request.request_id,
        user_id=data_request.user_id,
        request_type=data_request.request_type,
        notification_email=data_request.notification_email,
        request_reason=data_request.request_reason,
        status=data_request.status,
        requested_at=data_request.requested_at,
        requested_by=data_request.requested_by,
        processed_at=data_request.processed_at,
        export_format=data_request.export_format,
        export_size_bytes=data_request.export_size_bytes,
        verification_required=bool(data_request.verification_token),
        verified=data_request.verified,
        error_message=data_request.error_message
    )


@router.get("/{request_id}", response_model=DataRequestResponse)
async def get_data_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get data request status"""
    # Get request
    result = await db.execute(
        select(DataRequest).where(DataRequest.request_id == request_id)
    )
    data_request = result.scalar_one_or_none()
    
    if not data_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data request not found"
        )
    
    # Validate access
    if str(data_request.user_id) != current_user["user_id"] and \
       "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's data request"
        )
    
    return DataRequestResponse(
        id=data_request.id,
        request_id=data_request.request_id,
        user_id=data_request.user_id,
        request_type=data_request.request_type,
        notification_email=data_request.notification_email,
        request_reason=data_request.request_reason,
        status=data_request.status,
        requested_at=data_request.requested_at,
        requested_by=data_request.requested_by,
        processed_at=data_request.processed_at,
        export_format=data_request.export_format,
        export_size_bytes=data_request.export_size_bytes,
        verification_required=bool(data_request.verification_token),
        verified=data_request.verified,
        error_message=data_request.error_message
    )


@router.post("/{request_id}/cancel", response_model=DataRequestResponse)
async def cancel_data_request(
    request_id: str,
    cancel_data: DataRequestCancel,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cancel a pending data request"""
    # Get request
    result = await db.execute(
        select(DataRequest).where(DataRequest.request_id == request_id)
    )
    data_request = result.scalar_one_or_none()
    
    if not data_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data request not found"
        )
    
    # Validate access
    if str(data_request.user_id) != current_user["user_id"] and \
       "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel another user's data request"
        )
    
    # Check if can be cancelled
    if data_request.status not in [DataRequestStatus.PENDING, DataRequestStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel request with status: {data_request.status.value}"
        )
    
    # Cancel request
    data_request.status = DataRequestStatus.CANCELLED
    data_request.processing_notes = cancel_data.cancellation_reason
    await db.commit()
    
    return DataRequestResponse(
        id=data_request.id,
        request_id=data_request.request_id,
        user_id=data_request.user_id,
        request_type=data_request.request_type,
        notification_email=data_request.notification_email,
        request_reason=data_request.request_reason,
        status=data_request.status,
        requested_at=data_request.requested_at,
        requested_by=data_request.requested_by,
        processed_at=data_request.processed_at,
        export_format=data_request.export_format,
        export_size_bytes=data_request.export_size_bytes,
        verification_required=bool(data_request.verification_token),
        verified=data_request.verified,
        error_message=data_request.error_message
    )


@router.get("/user/{user_id}", response_model=List[DataRequestResponse])
async def get_user_data_requests(
    user_id: UUID,
    status: Optional[DataRequestStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all data requests for a user"""
    # Validate access
    if str(user_id) != current_user["user_id"] and \
       "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's data requests"
        )
    
    # Build query
    query = select(DataRequest).where(DataRequest.user_id == user_id)
    if status:
        query = query.where(DataRequest.status == status)
    query = query.order_by(DataRequest.requested_at.desc())
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    return [
        DataRequestResponse(
            id=r.id,
            request_id=r.request_id,
            user_id=r.user_id,
            request_type=r.request_type,
            notification_email=r.notification_email,
            request_reason=r.request_reason,
            status=r.status,
            requested_at=r.requested_at,
            requested_by=r.requested_by,
            processed_at=r.processed_at,
            export_format=r.export_format,
            export_size_bytes=r.export_size_bytes,
            verification_required=bool(r.verification_token),
            verified=r.verified,
            error_message=r.error_message
        )
        for r in requests
    ]


# Background task functions
async def process_data_export_request(
    request_id: str,
    export_request: Optional[DataRequestCreate],
    db: AsyncSession
):
    """Process data export request in background"""
    try:
        export_service = DataExportService(db)
        
        # Get request details
        result = await db.execute(
            select(DataRequest).where(DataRequest.request_id == request_id)
        )
        data_request = result.scalar_one_or_none()
        
        if not data_request:
            return
        
        # Create export request
        if not export_request:
            export_request = DataExportRequest(
                user_id=data_request.user_id,
                format=data_request.export_format or "json",
                include_metadata=True,
                anonymize_data=False
            )
        
        await export_service.process_export_request(request_id, export_request)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing export request: {str(e)}")


async def process_deletion_request(
    request_id: str,
    db: AsyncSession
):
    """Process deletion request in background"""
    try:
        deletion_service = DataDeletionService(db)
        await deletion_service.process_deletion_request(request_id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing deletion request: {str(e)}")