"""Anycast IP API routes."""
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_anycast_service, get_ipinfo_client, get_geolite_client
from domain.services import AnycastService
import logging

logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/anycast", tags=["anycast"])


@router.get("/ips")
async def get_anycast_ips(
    anycast_service: AnycastService = Depends(get_anycast_service),
):
    """Get list of anycast IPs."""
    try:
        ips = anycast_service.get_anycast_ips()
        return {
            "total": len(ips),
            "ips": ips,
        }
    except Exception as e:
        logger.error(f"Error fetching anycast IPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enrich")
async def enrich_anycast_ips(
    anycast_service: AnycastService = Depends(get_anycast_service),
):
    """Enrich anycast IPs with geolocation data."""
    try:
        async with get_ipinfo_client() as ipinfo, get_geolite_client() as geolite:
            result = await anycast_service.enrich_anycast_ips(
                ipinfo_client=ipinfo,
                geolite_client=geolite,
            )
        return result
    except Exception as e:
        logger.error(f"Error enriching anycast IPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
