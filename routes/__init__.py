"""
KoSPA Routes Package
====================
FastAPI routers for different endpoint groups.

This package contains:
- pages: HTML page rendering routes
- auth: User authentication endpoints
- analysis: Sound analysis API endpoints
"""

from .pages import router as pages_router
from .auth import router as auth_router
from .analysis import router as analysis_router

__all__ = ["pages_router", "auth_router", "analysis_router"]
