"""API routes."""
from .measurement_routes import router as measurement_router
from .probe_routes import router as probe_router
from .anycast_routes import router as anycast_router

__all__ = [
    "measurement_router",
    "probe_router",
    "anycast_router",
]
