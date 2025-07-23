"""
Storage services module
"""

from .storage_service import (
    StorageService,
    get_storage_service,
    close_storage_service
)

__all__ = [
    'StorageService',
    'get_storage_service',
    'close_storage_service'
]