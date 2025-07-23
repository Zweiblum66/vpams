"""
gRPC module for Integration Service
"""

from .server import serve, IntegrationServicer
from .client import IntegrationServiceClient

__all__ = ["serve", "IntegrationServicer", "IntegrationServiceClient"]