"""Measurement API routes."""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from repositories.measurement_repository import MeasurementRepository
from repositories.measurement_repository import MeasurementRepository
import tempfile
import logging
from functools import lru_cache

from services.measurement_service import MeasurementService
from services.probe_service import ProbeService


logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/measurements", tags=["measurements"])


@lru_cache()
def get_measurement_service() -> MeasurementService:
    """Get MeasurementService instance."""    
    return MeasurementService(
        measurement_repository=MeasurementRepository(),
        probe_service=ProbeService(),
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

