"""
GraphQL API routes for Integration Service
"""

from fastapi import APIRouter, Depends, Request
from strawberry.fastapi import GraphQLRouter
from typing import Dict, Any

from ..core.auth import get_current_user
from .graphql_schema import schema

router = APIRouter(tags=["graphql"])


async def get_context(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get GraphQL context with authentication"""
    return {
        "request": request,
        "current_user": current_user
    }


# Create GraphQL router with authentication
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
    path="/graphql"
)

# Mount GraphQL router
router.include_router(graphql_app, prefix="/api/v1")