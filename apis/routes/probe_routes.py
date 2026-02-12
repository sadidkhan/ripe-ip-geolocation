"""Probe API routes."""
from fastapi import APIRouter, Depends, HTTPException
from db.db import get_db
from repositories.probe_repository import ProbeRepository
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from services.probe_service import ProbeService
from services.measurement_service import MeasurementService

logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/probes", tags=["probes"])

def get_probe_service() -> ProbeService:
    return ProbeService()


def get_probe_service_with_db(session: AsyncSession = Depends(get_db)) -> ProbeService:
    """Get ProbeService instance with database repository."""
    repo = ProbeRepository(session=session)
    return ProbeService(probe_repository=repo)

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


# ============================================
# DATABASE ENDPOINTS
# ============================================

@router.get("/db/all")
async def get_all_probes_from_db(
    probe_service: ProbeService = Depends(get_probe_service_with_db),
):
    """Get all probes from database."""
    try:
        probes = await probe_service.get_all_probes_from_db()
        return {
            "status": "success",
            "count": len(probes),
            "probes": [
                {
                    "id": p.id,
                    "country_code": p.country_code,
                    "status": p.status,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "is_anchor": p.is_anchor,
                }
                for p in probes
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching probes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/country/{country_code}")
async def get_probes_by_country(
    country_code: str,
    probe_service: ProbeService = Depends(get_probe_service_with_db),
):
    """Get all probes for a specific country from database."""
    try:
        probes = await probe_service.get_probes_by_country_from_db(country_code.upper())
        
        return {
            "status": "success",
            "country_code": country_code.upper(),
            "count": len(probes),
            "probes": [
                {
                    "id": p.id,
                    "country_code": p.country_code,
                    "status": p.status,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "is_anchor": p.is_anchor,
                }
                for p in probes
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching probes for {country_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/{probe_id}")
async def get_probe_from_db(
    probe_id: int,
    probe_service: ProbeService = Depends(get_probe_service_with_db),
):
    """Get a specific probe from database by ID."""
    try:
        probe = await probe_service.get_probe_from_db(probe_id)
        
        if not probe:
            raise HTTPException(status_code=404, detail="Probe not found")
        
        return {
            "status": "success",
            "probe": {
                "id": probe.id,
                "country_code": probe.country_code,
                "status": probe.status,
                "latitude": probe.latitude,
                "longitude": probe.longitude,
                "asn_v4": probe.asn_v4,
                "asn_v6": probe.asn_v6,
                "is_anchor": probe.is_anchor,
                "is_public": probe.is_public,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching probe {probe_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))