"""
Validation Utilities

Utility functions for common validation tasks and FastAPI dependencies.
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from uuid import UUID
from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel, Field, validator

from core.validation import get_sanitizer, get_validator
from core.validation_middleware import (
    get_sanitized_headers,
    get_sanitized_query_params,
    get_sanitized_json,
    get_sanitized_form
)
from core.exceptions import ValidationException


# Common validation patterns
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')
VERSION_PATTERN = re.compile(r'^v?\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?$')
HEX_COLOR_PATTERN = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')


class ValidationSchema(BaseModel):
    """Base validation schema with common validators"""
    
    @validator('*', pre=True)
    def sanitize_strings(cls, v):
        """Sanitize all string fields"""
        if isinstance(v, str):
            sanitizer = get_sanitizer()
            return sanitizer.sanitize_string(v)
        return v


class PaginationParams(ValidationSchema):
    """Pagination parameters validation"""
    page: int = Field(default=1, ge=1, le=10000, description="Page number")
    limit: int = Field(default=20, ge=1, le=1000, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.limit


class SortingParams(ValidationSchema):
    """Sorting parameters validation"""
    sort_by: Optional[str] = Field(None, max_length=50, description="Field to sort by")
    sort_order: Optional[str] = Field(default="asc", regex=r'^(asc|desc)$', description="Sort order")
    
    @validator('sort_by')
    def validate_sort_field(cls, v):
        """Validate sort field name"""
        if v and not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid sort field name")
        return v


class FilterParams(ValidationSchema):
    """Common filter parameters"""
    search: Optional[str] = Field(None, max_length=500, description="Search query")
    status: Optional[str] = Field(None, max_length=50, description="Status filter")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    
    @validator('search')
    def validate_search_query(cls, v):
        """Validate search query"""
        if v:
            # Remove excessive whitespace
            v = re.sub(r'\s+', ' ', v.strip())
            # Check for minimum length
            if len(v) < 2:
                raise ValueError("Search query must be at least 2 characters")
        return v


class UUIDParam(ValidationSchema):
    """UUID parameter validation"""
    id: str = Field(..., description="UUID identifier")
    
    @validator('id')
    def validate_uuid(cls, v):
        """Validate UUID format"""
        if not UUID_PATTERN.match(v):
            raise ValueError("Invalid UUID format")
        return v


class SlugParam(ValidationSchema):
    """Slug parameter validation"""
    slug: str = Field(..., max_length=100, description="URL slug")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        if not SLUG_PATTERN.match(v):
            raise ValueError("Invalid slug format")
        return v


class UsernameParam(ValidationSchema):
    """Username parameter validation"""
    username: str = Field(..., description="Username")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not USERNAME_PATTERN.match(v):
            raise ValueError("Invalid username format")
        return v


class VersionParam(ValidationSchema):
    """Version parameter validation"""
    version: str = Field(..., description="Version string")
    
    @validator('version')
    def validate_version(cls, v):
        """Validate version format"""
        if not VERSION_PATTERN.match(v):
            raise ValueError("Invalid version format")
        return v


class EmailParam(ValidationSchema):
    """Email parameter validation"""
    email: str = Field(..., description="Email address")
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        sanitizer = get_sanitizer()
        return sanitizer.sanitize_email(v)


class URLParam(ValidationSchema):
    """URL parameter validation"""
    url: str = Field(..., description="URL")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format"""
        sanitizer = get_sanitizer()
        return sanitizer.sanitize_url(v)


class IPAddressParam(ValidationSchema):
    """IP address parameter validation"""
    ip_address: str = Field(..., description="IP address")
    
    @validator('ip_address')
    def validate_ip(cls, v):
        """Validate IP address format"""
        sanitizer = get_sanitizer()
        return sanitizer.sanitize_ip_address(v)


class ColorParam(ValidationSchema):
    """Color parameter validation"""
    color: str = Field(..., description="Hex color code")
    
    @validator('color')
    def validate_color(cls, v):
        """Validate hex color format"""
        if not HEX_COLOR_PATTERN.match(v):
            raise ValueError("Invalid hex color format")
        return v


class PhoneParam(ValidationSchema):
    """Phone number parameter validation"""
    phone: str = Field(..., description="Phone number")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        if not PHONE_PATTERN.match(v):
            raise ValueError("Invalid phone number format")
        return v


# FastAPI dependency functions

def get_pagination_params(
    page: int = 1,
    limit: int = 20
) -> PaginationParams:
    """Get validated pagination parameters"""
    return PaginationParams(page=page, limit=limit)


def get_sorting_params(
    sort_by: Optional[str] = None,
    sort_order: str = "asc"
) -> SortingParams:
    """Get validated sorting parameters"""
    return SortingParams(sort_by=sort_by, sort_order=sort_order)


def get_filter_params(
    search: Optional[str] = None,
    status: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None
) -> FilterParams:
    """Get validated filter parameters"""
    return FilterParams(
        search=search,
        status=status,
        created_after=created_after,
        created_before=created_before
    )


def validate_uuid_param(uuid_str: str) -> str:
    """Validate UUID parameter"""
    try:
        param = UUIDParam(id=uuid_str)
        return param.id
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID: {e}"
        )


def validate_slug_param(slug: str) -> str:
    """Validate slug parameter"""
    try:
        param = SlugParam(slug=slug)
        return param.slug
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid slug: {e}"
        )


def validate_username_param(username: str) -> str:
    """Validate username parameter"""
    try:
        param = UsernameParam(username=username)
        return param.username
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid username: {e}"
        )


def validate_email_param(email: str) -> str:
    """Validate email parameter"""
    try:
        param = EmailParam(email=email)
        return param.email
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email: {e}"
        )


def validate_url_param(url: str) -> str:
    """Validate URL parameter"""
    try:
        param = URLParam(url=url)
        return param.url
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL: {e}"
        )


def validate_ip_address_param(ip_address: str) -> str:
    """Validate IP address parameter"""
    try:
        param = IPAddressParam(ip_address=ip_address)
        return param.ip_address
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IP address: {e}"
        )


def validate_request_data(request: Request) -> Dict[str, Any]:
    """Get all sanitized request data"""
    return {
        "headers": get_sanitized_headers(request),
        "query_params": get_sanitized_query_params(request),
        "json": get_sanitized_json(request),
        "form": get_sanitized_form(request)
    }


def validate_content_type(request: Request, allowed_types: List[str]) -> str:
    """Validate request content type"""
    content_type = request.headers.get("content-type", "")
    
    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content-Type header is required"
        )
    
    # Extract base content type (remove charset, etc.)
    base_content_type = content_type.split(';')[0].strip().lower()
    
    if base_content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {base_content_type}. Allowed: {allowed_types}"
        )
    
    return base_content_type


def validate_json_schema(request: Request, schema: BaseModel) -> BaseModel:
    """Validate JSON request body against Pydantic schema"""
    json_data = get_sanitized_json(request)
    
    if json_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSON body is required"
        )
    
    try:
        return schema(**json_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e}"
        )


def validate_file_upload(request: Request, max_size: int = 10 * 1024 * 1024) -> Dict[str, Any]:
    """Validate file upload from multipart form"""
    from core.validation_middleware import get_sanitized_multipart_form
    
    multipart_data = get_sanitized_multipart_form(request)
    
    if not multipart_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded"
        )
    
    # Find file fields
    file_fields = {k: v for k, v in multipart_data.items() if isinstance(v, dict) and 'filename' in v}
    
    if not file_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file fields found"
        )
    
    # Validate file sizes
    for field_name, file_info in file_fields.items():
        if file_info.get('size', 0) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File {field_name} is too large (max {max_size} bytes)"
            )
    
    return file_fields


def validate_api_version(version: str) -> str:
    """Validate API version format"""
    if not re.match(r'^v\d+$', version):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API version format. Expected format: v1, v2, etc."
        )
    return version


def validate_datetime_range(start: Optional[datetime], end: Optional[datetime]) -> None:
    """Validate datetime range"""
    if start and end:
        if start >= end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start datetime must be before end datetime"
            )
        
        # Check if range is too large (more than 1 year)
        if (end - start).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 1 year"
            )


def validate_numeric_range(value: Union[int, float], min_val: Optional[Union[int, float]] = None, max_val: Optional[Union[int, float]] = None) -> Union[int, float]:
    """Validate numeric range"""
    if min_val is not None and value < min_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value {value} is below minimum {min_val}"
        )
    
    if max_val is not None and value > max_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value {value} is above maximum {max_val}"
        )
    
    return value


def validate_string_length(value: str, min_length: int = 0, max_length: int = 10000) -> str:
    """Validate string length"""
    if len(value) < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"String too short (minimum {min_length} characters)"
        )
    
    if len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"String too long (maximum {max_length} characters)"
        )
    
    return value


def validate_choice(value: str, choices: List[str]) -> str:
    """Validate value against list of choices"""
    if value not in choices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid choice: {value}. Valid choices: {choices}"
        )
    return value


def validate_regex_pattern(value: str, pattern: str, error_message: str) -> str:
    """Validate string against regex pattern"""
    if not re.match(pattern, value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    return value


# Common dependency combinations

def validate_list_request(
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortingParams = Depends(get_sorting_params),
    filters: FilterParams = Depends(get_filter_params)
) -> Dict[str, Any]:
    """Validate common list request parameters"""
    return {
        "pagination": pagination,
        "sorting": sorting,
        "filters": filters
    }


def validate_search_request(
    query: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortingParams = Depends(get_sorting_params)
) -> Dict[str, Any]:
    """Validate search request parameters"""
    # Validate search query
    if len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    return {
        "query": query.strip(),
        "pagination": pagination,
        "sorting": sorting
    }
