"""GeoLite client - moved to infrastructure/clients/geolite_client.py"""
# This file is kept for backwards compatibility
from infrastructure.clients.geolite_client import GeoLiteClient, GeoLiteResult

__all__ = ["GeoLiteClient", "GeoLiteResult"]
            accuracy_radius_km=data.get("location", {}).get("accuracy_radius"),
        )
