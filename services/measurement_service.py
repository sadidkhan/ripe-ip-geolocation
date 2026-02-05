import asyncio
import logging
from typing import Literal, AsyncGenerator

from fastapi import Path


from anycast_ip_collection import get_anycast_ips
from models.measurement import Measurement
from repositories.measurement_repository import MeasurementRepository
from ripe_atlas_client import RipeAtlasClient
from services.probe_service import ProbeService

logger = logging.getLogger("ripe_atlas")

class MeasurementService:
    """Service for managing and processing measurements."""
    
    def __init__(self, probe_service: ProbeService, measurement_repository: MeasurementRepository):
        """Initialize the MeasurementService."""
        self.probe_service = probe_service
        self.repo = measurement_repository
        self.rate_limit_count = 90  # Number of requests before sleeping
        self.rate_limit_sleep = 800   # Sleep duration in seconds
        
    
    
    async def create_measurements(
        self,
        continent_code: str = "AF",
        measurement_type: Literal["ping", "traceroute"] = "ping"
    ) -> dict:
        """Create measurements for multiple targets with rate limiting."""
        # Check what's already done
        measurements_csv = f"data/measurements/measurements_{continent_code.lower()}.csv"
        targets = get_anycast_ips()
        
        existing_measurements = self.repo.read_all_measurements(measurements_csv)
        
        if len(existing_measurements) >= len(targets):
            return {
                "status": "complete",
                "message": "All measurements have already been created.",
                "created": 0,
            }
        
        # Filter out targets that already have measurements
        targets_to_process = [t for t in targets if t not in existing_measurements]
        
        probes = await self.probe_service.get_continent_probes(continent_code)        
        if not probes:
            return {
                "status": "complete",
                "message": "No probes available to create a measurement.",
                "created": 0,
            }
        # Create probe string
        probe_ids_string = ",".join(str(probe["id"]) for probe in probes)
        
        measurements_created = 0
        counter = 0
        
        logger.info(f"Creating measurements for {len(targets_to_process)} targets")
        
        async with RipeAtlasClient() as client:
            for target in targets_to_process:
                try:
                    counter += 1
                    
                    # Create the measurement
                    measurement_data = self._build_measurement_data(
                        target, probe_ids_string, len(probes), measurement_type
                    )
                    
                    response = await client.create_measurement(target, measurement_data)
                    measurement_ids = response.get("measurements", [])
                    
                    if measurement_ids:
                        msm_id = measurement_ids[0]
                        measurement = Measurement(
                            id=msm_id,
                            target=target,
                            measurement_type=measurement_type,
                            status="pending",
                        )
                        self.repo.write_measurement(measurement, measurements_csv)
                        measurements_created += 1
                        logger.info(f"Created measurement {msm_id} for {target}")
                    
                    # Rate limiting
                    if counter >= self.rate_limit_count:
                        logger.info(f"Rate limit reached, sleeping for {self.rate_limit_sleep}s")
                        await asyncio.sleep(self.rate_limit_sleep)
                        counter = 0
                
                except Exception as e:
                    logger.error(f"Error creating measurement for {target}: {e}")
        
        return {
            "status": "success",
            "message": f"Created {measurements_created} new measurements.",
            "created": measurements_created,
        }
    
    def _build_measurement_data(
        self,
        target: str,
        probe_ids_string: str,
        num_probes: int,
        measurement_type: Literal["ping", "traceroute"] = "ping"
    ) -> dict:
        """Build measurement data structure for RIPE Atlas API."""
        return {
            "definitions": [
                {
                    "target": target,
                    "description": f"{measurement_type} measurement for {target}",
                    "type": measurement_type,
                    "af": "4",
                    "is_oneoff": True,
                }
            ],
            "probes": [
                {
                    "requested": num_probes,
                    "type": "probes",
                    "value": probe_ids_string,
                }
            ],
        }