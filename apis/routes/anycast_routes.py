from fastapi import APIRouter, HTTPException
import logging

from anycast_ip_collection import fetch_anycast_hostnames_csv

logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/anycast", tags=["anycast"])


@router.post("/fetch-hostnames")
async def fetch_anycast_hostnames():
    """Trigger fetching hostnames for anycast IPs and writing to CSV."""
    try:
        result = await fetch_anycast_hostnames_csv()
        return result
    except Exception as e:
        logger.error("Error fetching hostnames: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
