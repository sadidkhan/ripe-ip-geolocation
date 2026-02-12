"""Measurement API routes."""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from repositories.measurement_repository import MeasurementRepository
from repositories.probe_repository import ProbeRepository
from db.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import tempfile
import logging
from functools import lru_cache

from services.measurement_service import MeasurementService
from services.probe_service import ProbeService


logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/measurements", tags=["measurements"])


def get_measurement_service(session: AsyncSession = Depends(get_db)) -> MeasurementService:
    """Get MeasurementService instance with database repositories."""    
    measurement_repo = MeasurementRepository(session=session)
    probe_repo = ProbeRepository(session=session)
    probe_service = ProbeService(probe_repository=probe_repo)
    return MeasurementService(
        measurement_repository=measurement_repo,
        probe_service=probe_service,
    )

@router.post("/initiate/{continent_code}")
async def initiate_measurements(
    continent_code: str,
    measurement_service: MeasurementService = Depends(get_measurement_service),
):
    """Initiate measurements for all anycast IPs using African probes."""
    try:
        if not continent_code or continent_code not in ["AF", "SA"]:
            raise HTTPException(status_code=400, detail="Invalid continent code")
        # Create measurements
        result = await measurement_service.create_measurements(
            continent_code=continent_code,
            measurement_type="ping",
        )
        
        return result
    except Exception as e:
        logger.error(f"Error initiating measurements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-results/{continent_code}")
async def process_measurement_results(
    continent_code: str,
    measurement_service: MeasurementService = Depends(get_measurement_service),
):
    """Process and save measurement results."""
    try:
        result = await measurement_service.fetch_measurement_results(continent_code=continent_code)
        return result
    except Exception as e:
        logger.error(f"Error processing results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/{measurement_id}")
# async def get_measurement(
#     measurement_id: int,
#     measurement_service: MeasurementService = Depends(get_measurement_service),
# ):
#     """Get a specific measurement by ID."""
#     try:
#         ripe_client = get_ripe_atlas_client()
#         result = await measurement_service.get_measurement_by_id(measurement_id, ripe_client)
#         return result
#     except Exception as e:
#         logger.error(f"Error fetching measurement {measurement_id}: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DATABASE ENDPOINTS
# ============================================

@router.get("/get_measurments_for_target_analysis")
async def get_measurments_for_target_analysis(
    measurement_service: MeasurementService = Depends(get_measurement_service),
):
    """Get all measurements from database."""
    try:
        measurements = await measurement_service.get_measurement_for_target_analysis()
        return {
            "status": "success",
            "count": len(measurements),
            "measurements": measurements
        }
    except Exception as e:
        logger.error(f"Error fetching measurements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/{measurement_id}")
async def get_measurement_from_db(
    measurement_id: int,
    measurement_service: MeasurementService = Depends(get_measurement_service),
):
    """Get a specific measurement from database by ID."""
    try:
        measurement = await measurement_service.get_measurement_from_db(measurement_id)
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        return {
            "status": "success",
            "measurement": {
                "id": measurement.id,
                "target": measurement.target,
                "type": measurement.measurement_type,
                "status": measurement.status,
                "created_at": measurement.created_at.isoformat() if measurement.created_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching measurement {measurement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/db/{measurement_id}/status")
async def update_measurement_status(
    measurement_id: int,
    new_status: str,
    measurement_service: MeasurementService = Depends(get_measurement_service),
):
    """Update measurement status in database."""
    try:
        result = await measurement_service.update_measurement_status_in_db(measurement_id, new_status)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return {"status": "success", "message": f"Measurement {measurement_id} updated to {new_status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating measurement {measurement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

