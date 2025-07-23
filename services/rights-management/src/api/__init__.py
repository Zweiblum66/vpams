"""
Rights Management Service - API Module
"""

from . import routes
from . import restriction_routes
from . import geo_blocking_routes

__all__ = [
    "routes",
    "restriction_routes", 
    "geo_blocking_routes"
]