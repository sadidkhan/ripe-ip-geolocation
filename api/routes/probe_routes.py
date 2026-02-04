"""Probe API routes."""
from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_probe_service, get_ripe_atlas_client
from domain.services import ProbeService
import logging

logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/probes", tags=["probes"])


@router.get("/")
async def get_all_probes(
    probe_service: ProbeService = Depends(get_probe_service),
):
    """Get all active probes."""
    try:
        ripe_client = get_ripe_atlas_client()
        probes = await probe_service.get_all_probes(ripe_client)
        return {
            "total": len(probes),
            "probes": [probe.to_dict() for probe in probes],
        }
    except Exception as e:
        logger.error(f"Error fetching probes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/african")
async def get_african_probes(
    probe_service: ProbeService = Depends(get_probe_service),
):
    """Get African probes only."""
    try:
        ripe_client = get_ripe_atlas_client()
        probes = await probe_service.get_african_probes(ripe_client)
        return {
            "total": len(probes),
            "probes": [probe.to_dict() for probe in probes],
        }
    except Exception as e:
        logger.error(f"Error fetching African probes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
