"""Measurement API routes."""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from api.dependencies import get_measurement_service, get_probe_service, get_anycast_service
from api.dependencies import get_ripe_atlas_client, get_ipinfo_client, get_geolite_client
from domain.services import MeasurementService, ProbeService, AnycastService
from infrastructure.clients import RipeAtlasClient, IpinfoClient, GeoLiteClient
from infrastructure.parsers.ripe_measurement_parser import RipeMeasurementParser
import tempfile
import logging

logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.post("/initiate")
async def initiate_measurements(
    measurement_service: MeasurementService = Depends(get_measurement_service),
    probe_service: ProbeService = Depends(get_probe_service),
    anycast_service: AnycastService = Depends(get_anycast_service),
):
    """Initiate measurements for all anycast IPs using African probes."""
    try:
        # Get resources
        targets = anycast_service.get_anycast_ips()
        ripe_client = get_ripe_atlas_client()
        african_probes = await probe_service.get_african_probes(ripe_client)
        
        if not african_probes:
            raise HTTPException(status_code=400, detail="No African probes available")
        
        # Create probe string
        probe_ids_string = probe_service.get_probe_ids_string(african_probes)
        
        # Create measurements
        result = await measurement_service.create_measurements(
            targets=targets,
            probe_ids_string=probe_ids_string,
            num_probes=len(african_probes),
            ripe_client=ripe_client,
            measurement_type="ping",
        )
        
        return result
    except Exception as e:
        logger.error(f"Error initiating measurements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-results")
async def process_measurement_results(
    measurement_service: MeasurementService = Depends(get_measurement_service),
):
    """Process and save measurement results."""
    try:
        ripe_client = get_ripe_atlas_client()
        result = await measurement_service.process_and_save_results(ripe_client)
        return result
    except Exception as e:
        logger.error(f"Error processing results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{measurement_id}")
async def get_measurement(
    measurement_id: int,
    measurement_service: MeasurementService = Depends(get_measurement_service),
):
    """Get a specific measurement by ID."""
    try:
        ripe_client = get_ripe_atlas_client()
        result = await measurement_service.get_measurement_by_id(measurement_id, ripe_client)
        return result
    except Exception as e:
        logger.error(f"Error fetching measurement {measurement_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_measurement_file(
    file: UploadFile = File(...),
):
    """Upload and process a RIPE Atlas measurement file."""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        
        # Parse the file
        parser = RipeMeasurementParser(tmp_path)
        measurements = parser.parse_measurements()
        
        # Enrich with geolocation data
        async with get_ipinfo_client() as ipinfo, get_geolite_client() as geolite:
            for measurement in measurements:
                for trace in measurement["traceroute"]:
                    ip = trace["from"]
                    if ip == "*" or ip is None:
                        trace["ipinfo"] = None
                        trace["geolite"] = None
                        continue
                    
                    ipinfo_data = await ipinfo.lookup(ip)
                    
                    try:
                        geolite_data = await geolite.city(ip)
                    except Exception as e:
                        logger.error(f"Error fetching GeoLite data for {ip}: {e}")
                        geolite_data = {}
                    
                    trace["ipinfo"] = ipinfo_data
                    trace["geolite"] = geolite_data
        
        return measurements
    except Exception as e:
        logger.error(f"Error uploading measurement file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
