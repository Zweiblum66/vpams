"""
API routes for approval workflows
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from ..core.auth import get_current_user
from ..db.base import get_db
from ..services.approval_service import ApprovalService
from ..models.approval_schemas import (
    CreateApprovalRequest, UpdateApprovalDecision, DelegateApprovalRequest,
    ApprovalSearchRequest, ApprovalRequest, ApprovalDecision,
    ApprovalResponse, ApprovalListResponse, ApprovalDashboard,
    ApprovalStatus, ApprovalTemplate
)

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])
approval_service = ApprovalService()


@router.post("/", response_model=ApprovalRequest, status_code=status.HTTP_201_CREATED)
async def create_approval(
    request: CreateApprovalRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new approval request"""
    try:
        approval = await approval_service.create_approval_request(
            db=db,
            user_id=current_user["user_id"],
            request=request
        )
        return approval
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{request_id}", response_model=ApprovalRequest)
async def get_approval(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get an approval request by ID"""
    approval = await approval_service.get_approval_request(request_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found"
        )
    
    # Check if user has access to this approval
    approver_ids = [a.identifier for a in approval.approval_config.approvers]
    if (current_user["user_id"] != approval.requestor_id and 
        current_user["user_id"] not in approver_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this approval"
        )
    
    return approval


@router.post("/{request_id}/decisions", response_model=ApprovalDecision)
async def make_approval_decision(
    request_id: str,
    decision: UpdateApprovalDecision,
    current_user: dict = Depends(get_current_user)
):
    """Make an approval decision"""
    try:
        approval_decision = await approval_service.update_approval_decision(
            request_id=request_id,
            approver_id=current_user["user_id"],
            decision_update=decision
        )
        return approval_decision
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/delegate", response_model=ApprovalRequest)
async def delegate_approval(
    request_id: str,
    delegation: DelegateApprovalRequest,
    current_user: dict = Depends(get_current_user)
):
    """Delegate an approval to another approver"""
    try:
        approval = await approval_service.delegate_approval(
            request_id=request_id,
            approver_id=current_user["user_id"],
            delegation=delegation
        )
        return approval
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/search", response_model=ApprovalListResponse)
async def search_approvals(
    search_request: ApprovalSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search for approval requests"""
    try:
        # Add user context to search if not admin
        if not current_user.get("is_admin", False):
            # Limit search to user's approvals
            if not search_request.approver_id and not search_request.requestor_id:
                search_request.approver_id = current_user["user_id"]
        
        results = await approval_service.search_approvals(search_request)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=ApprovalListResponse)
async def list_approvals(
    status: Optional[List[ApprovalStatus]] = Query(None),
    approver_id: Optional[str] = None,
    requestor_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    deadline_before: Optional[datetime] = None,
    tags: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", regex="^(created_at|deadline_at|status|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: dict = Depends(get_current_user)
):
    """List approval requests with filters"""
    search_request = ApprovalSearchRequest(
        status=status,
        approver_id=approver_id,
        requestor_id=requestor_id,
        workflow_id=workflow_id,
        created_after=created_after,
        created_before=created_before,
        deadline_before=deadline_before,
        tags=tags,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Add user context if not admin
    if not current_user.get("is_admin", False):
        if not approver_id and not requestor_id:
            search_request.approver_id = current_user["user_id"]
    
    try:
        results = await approval_service.search_approvals(search_request)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/dashboard/me", response_model=ApprovalDashboard)
async def get_my_approval_dashboard(
    current_user: dict = Depends(get_current_user)
):
    """Get approval dashboard for current user"""
    try:
        dashboard = await approval_service.get_approval_dashboard(
            user_id=current_user["user_id"]
        )
        return dashboard
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/dashboard/{user_id}", response_model=ApprovalDashboard)
async def get_user_approval_dashboard(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get approval dashboard for a specific user (admin only)"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view other users' dashboards"
        )
    
    try:
        dashboard = await approval_service.get_approval_dashboard(user_id=user_id)
        return dashboard
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/cancel", response_model=ApprovalRequest)
async def cancel_approval(
    request_id: str,
    reason: str = Query(..., description="Reason for cancellation"),
    current_user: dict = Depends(get_current_user)
):
    """Cancel an approval request"""
    approval = await approval_service.get_approval_request(request_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found"
        )
    
    # Check if user is the requestor
    if current_user["user_id"] != approval.requestor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requestor can cancel an approval"
        )
    
    # Check if approval can be cancelled
    if approval.status not in [ApprovalStatus.PENDING, ApprovalStatus.ESCALATED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel approval in {approval.status} status"
        )
    
    # Cancel the approval
    approval.status = ApprovalStatus.CANCELLED
    approval.completed_at = datetime.utcnow()
    approval.final_comments = f"Cancelled by requestor: {reason}"
    
    return approval


@router.get("/pending/count", response_model=dict)
async def get_pending_approval_count(
    current_user: dict = Depends(get_current_user)
):
    """Get count of pending approvals for current user"""
    dashboard = await approval_service.get_approval_dashboard(
        user_id=current_user["user_id"]
    )
    return {
        "pending_count": dashboard.pending_count,
        "upcoming_deadlines": len(dashboard.upcoming_deadlines)
    }


@router.post("/bulk/approve", response_model=dict)
async def bulk_approve(
    request_ids: List[str],
    comments: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Bulk approve multiple requests"""
    results = {
        "successful": [],
        "failed": []
    }
    
    for request_id in request_ids:
        try:
            decision = UpdateApprovalDecision(
                decision=ApprovalStatus.APPROVED,
                comments=comments or "Bulk approved"
            )
            
            await approval_service.update_approval_decision(
                request_id=request_id,
                approver_id=current_user["user_id"],
                decision_update=decision
            )
            results["successful"].append(request_id)
        except Exception as e:
            results["failed"].append({
                "request_id": request_id,
                "error": str(e)
            })
    
    return results


@router.post("/bulk/reject", response_model=dict)
async def bulk_reject(
    request_ids: List[str],
    comments: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Bulk reject multiple requests"""
    results = {
        "successful": [],
        "failed": []
    }
    
    for request_id in request_ids:
        try:
            decision = UpdateApprovalDecision(
                decision=ApprovalStatus.REJECTED,
                comments=comments or "Bulk rejected"
            )
            
            await approval_service.update_approval_decision(
                request_id=request_id,
                approver_id=current_user["user_id"],
                decision_update=decision
            )
            results["successful"].append(request_id)
        except Exception as e:
            results["failed"].append({
                "request_id": request_id,
                "error": str(e)
            })
    
    return results


# Template endpoints (for future implementation)

@router.get("/templates", response_model=List[ApprovalTemplate])
async def list_approval_templates(
    category: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """List available approval templates"""
    # TODO: Implement template listing
    return []


@router.get("/templates/{template_id}", response_model=ApprovalTemplate)
async def get_approval_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get an approval template by ID"""
    # TODO: Implement template retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Template functionality not yet implemented"
    )


@router.post("/templates", response_model=ApprovalTemplate)
async def create_approval_template(
    template: ApprovalTemplate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new approval template"""
    # TODO: Implement template creation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Template functionality not yet implemented"
    )