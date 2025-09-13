# API routers package

from .tickets import router as tickets_router
from .admin import router as admin_router

__all__ = [
    'tickets_router',
    'admin_router'
]