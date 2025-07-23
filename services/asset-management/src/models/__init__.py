"""
Models module for Asset Management Service
"""

from .schemas import (
    # Pagination
    PaginationParams, PaginatedResponse,
    # Asset schemas
    AssetBase, AssetCreate, AssetUpdate, AssetResponse, AssetListResponse,
    # Asset version schemas
    AssetVersionCreate, AssetVersionResponse,
    # Upload schemas
    UploadInitiate, UploadResponse, UploadComplete,
    # Project container schemas
    ProjectContainerBase, ProjectContainerCreate, ProjectContainerUpdate,
    ProjectContainerResponse, ProjectContainerTree,
    # Tag schemas
    TagCreate, TagResponse,
    # Collection schemas
    CollectionCreate, CollectionUpdate, CollectionResponse,
    # Relationship schemas
    AssetRelationshipCreate, AssetRelationshipResponse,
    # Sharing schemas
    AssetShareCreate, AssetShareUpdate, AssetShareResponse,
    # Search schemas
    AssetSearchParams,
    # Bulk operation schemas
    BulkAssetUpdate, BulkOperationResponse
)

__all__ = [
    # Pagination
    'PaginationParams', 'PaginatedResponse',
    # Asset schemas
    'AssetBase', 'AssetCreate', 'AssetUpdate', 'AssetResponse', 'AssetListResponse',
    # Asset version schemas
    'AssetVersionCreate', 'AssetVersionResponse',
    # Upload schemas
    'UploadInitiate', 'UploadResponse', 'UploadComplete',
    # Project container schemas
    'ProjectContainerBase', 'ProjectContainerCreate', 'ProjectContainerUpdate',
    'ProjectContainerResponse', 'ProjectContainerTree',
    # Tag schemas
    'TagCreate', 'TagResponse',
    # Collection schemas
    'CollectionCreate', 'CollectionUpdate', 'CollectionResponse',
    # Relationship schemas
    'AssetRelationshipCreate', 'AssetRelationshipResponse',
    # Sharing schemas
    'AssetShareCreate', 'AssetShareUpdate', 'AssetShareResponse',
    # Search schemas
    'AssetSearchParams',
    # Bulk operation schemas
    'BulkAssetUpdate', 'BulkOperationResponse'
]