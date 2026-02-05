"""Probe API routes."""
from fastapi import APIRouter, Depends, HTTPException
import logging
from services.probe_service import ProbeService

logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/probes", tags=["probes"])

def get_probe_service() -> ProbeService:
    return ProbeService()

@router.get("/")
async def get_all_probes(
    probe_service: ProbeService = Depends(get_probe_service),
):
    """Get all active probes."""
    try:
        probes = await probe_service.get_all_probes()
        return {
            "total": len(probes),
            "probes": probes,
        }
    except Exception as e:
        logger.error(f"Error fetching probes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/probes/{continent}")
async def get_continent_probes(
    continent: str,
    probe_service: ProbeService = Depends(get_probe_service),
):
    """Get probes for a specific continent."""
    try:
        probes = await probe_service.get_continent_probes(continent)
        return {
            "total": len(probes),
            "probes": probes,
        }
    except Exception as e:
        logger.error(f"Error fetching probes for continent {continent}: {e}")
        raise HTTPException(status_code=500, detail=str(e))