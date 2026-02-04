"""Measurement service with business logic."""
import asyncio
import logging
from typing import Literal, AsyncGenerator
from domain.models import Measurement, PingResult, MeasurementResult
from infrastructure.repositories import MeasurementRepository

logger = logging.getLogger("ripe_atlas")


class MeasurementService:
    """Business logic for measurement operations."""
    
    def __init__(
        self,
        measurement_repository: MeasurementRepository,
        rate_limit_count: int = 90,
        rate_limit_sleep: int = 800,
        batch_sleep: int = 10,
    ):
        self.repo = measurement_repository
        self.rate_limit_count = rate_limit_count
        self.rate_limit_sleep = rate_limit_sleep
        self.batch_sleep = batch_sleep
    
    async def create_measurements(
        self,
        targets: list[str],
        probe_ids_string: str,
        num_probes: int,
        ripe_client,
        measurement_type: Literal["ping", "traceroute"] = "ping",
    ) -> dict:
        """Create measurements for multiple targets with rate limiting."""
        # Check what's already done
        existing_measurements = self.repo.read_all_measurements()
        
        if len(existing_measurements) >= len(targets):
            return {
                "status": "complete",
                "message": "All measurements have already been created.",
                "created": 0,
            }
        
        # Filter out targets that already have measurements
        targets_to_process = [t for t in targets if t not in existing_measurements]
        
        measurements_created = 0
        counter = 0
        
        logger.info(f"Creating measurements for {len(targets_to_process)} targets")
        
        async with ripe_client as client:
            for target in targets_to_process:
                try:
                    counter += 1
                    
                    # Create the measurement
                    measurement_data = self._build_measurement_data(
                        target, probe_ids_string, num_probes, measurement_type
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
                        self.repo.write_measurement(measurement)
                        measurements_created += 1
                        logger.info(f"Created measurement {msm_id} for {target}")
                    
                    # Rate limiting
                    if counter >= self.rate_limit_count:
                        logger.info(f"Rate limit reached, sleeping for {self.rate_limit_sleep}s")
                        await asyncio.sleep(self.rate_limit_sleep)
                        counter = 0
                
                except Exception as e:
                    logger.error(f"Error creating measurement for {target}: {e}")
                    self.repo.write_failed_measurement(target, str(e))
        
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
        measurement_type: str,
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
    
    async def fetch_measurement_results(
        self,
        ripe_client,
    ) -> AsyncGenerator[list[PingResult], None]:
        """Fetch results for all measurements that haven't been fetched yet."""
        all_measurements = self.repo.read_all_measurements()
        already_fetched = self.repo.read_fetched_results()
        
        measurements_to_fetch = [
            msm_id for msm_id in all_measurements.values()
            if msm_id not in already_fetched
        ]
        
        logger.info(f"Fetching results for {len(measurements_to_fetch)} measurements")
        
        counter = 0
        async with ripe_client as client:
            for msm_id in measurements_to_fetch:
                logger.info(f"Fetching results for measurement {msm_id}")
                
                try:
                    response = await client.get_measurement_result(msm_id)
                    
                    if response:
                        # Convert API response to domain models
                        ping_results = [
                            PingResult.from_api_response(result_data)
                            for result_data in response
                        ]
                        yield ping_results
                    
                    counter += 1
                    if counter % 10 == 0:
                        await asyncio.sleep(self.batch_sleep)
                
                except Exception as e:
                    logger.error(f"Error fetching results for measurement {msm_id}: {e}")
    
    async def process_and_save_results(self, ripe_client) -> dict:
        """Process measurement results and save them."""
        total_saved = 0
        
        async for ping_results in self.fetch_measurement_results(ripe_client):
            if ping_results:
                self.repo.write_ping_results(ping_results)
                total_saved += len(ping_results)
                logger.info(f"Saved {len(ping_results)} results")
        
        return {
            "status": "success",
            "message": f"Processed and saved {total_saved} results",
            "saved": total_saved,
        }
    
    async def get_measurement_by_id(self, measurement_id: int, ripe_client) -> dict:
        """Get a specific measurement by ID."""
        async with ripe_client as client:
            response = await client.get_measurement(measurement_id)
            return response
