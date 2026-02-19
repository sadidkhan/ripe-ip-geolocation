import asyncio
import logging
from typing import Literal, AsyncGenerator, Optional, List

from fastapi import Path
from sqlalchemy.ext.asyncio import AsyncSession

from anycast_ip_collection import get_anycast_ips
from models.measurement import Measurement, PingResult
from repositories.measurement_repository import MeasurementRepository
from ripe_atlas_client import RipeAtlasClient
from services.probe_service import ProbeService
import os
import json

logger = logging.getLogger("ripe_atlas")

class MeasurementService:
    """Service for managing and processing measurements."""
    
    def __init__(self, probe_service: ProbeService, measurement_repository: MeasurementRepository):
        """Initialize the MeasurementService."""
        self.probe_service = probe_service
        self.repo = measurement_repository
        self.rate_limit_count = 90  # Number of requests before sleeping
        self.rate_limit_sleep = 800   # Sleep duration in seconds
        self.initialize_key_list()
        self.ripe_client = RipeAtlasClient(api_key=self.get_api_key())
        
    def initialize_key_list(self) -> list: 
        """Get a dictionary of RIPE Atlas API keys."""
        keys = json.loads(os.environ["RIPE_ATLAS_API_KEYS"])
        key_list = []
        for key_name, key_value in keys.items():
            key = {}
            key["key"] = key_value
            key["is_used"] = False
            key_list.append(key)
            
        self.ripe_atlas_keys = key_list
    
    def get_api_key(self):
        """Initialize the RIPE Atlas client with the first available API key."""
        for key in self.ripe_atlas_keys:
            if not key["is_used"]:
                key["is_used"] = True
                return key["key"]
        return None
    
    async def create_measurements(
        self,
        continent_code: str = "AF",
        measurement_type: Literal["ping", "traceroute"] = "ping"
    ) -> dict:
        """Create measurements for multiple targets with rate limiting."""
        # Check what's already done
        measurements_csv = f"data/measurements/measurements_{continent_code.lower()}.csv"
        targets = get_anycast_ips(10)
        
        existing_measurements = self.repo.read_all_measurements(measurements_csv)
        
        if len(existing_measurements) >= len(targets):
            return {
                "status": "complete",
                "message": "All measurements have already been created.",
                "created": 0,
            }
        
        # Filter out targets that already have measurements
        targets_to_process = [t for t in targets if t not in existing_measurements]
        
        probes = await self.probe_service.get_filtered_probes(continent_code)
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
        #is_limit_exceed_error = False
        
         # Build measurement data template
        # async with self.ripe_client as client:
        #     for target in targets_to_process:
        #         try:
                    
        #             # Create the measurement
        #             measurement_data = self._build_measurement_data(
        #                 target, probe_ids_string, len(probes), measurement_type
        #             )
                    
        #             response = await client.create_measurement(target, measurement_data)
        #             measurement_ids = response.get("measurements", [])
                    
        #             if measurement_ids:
        #                 msm_id = measurement_ids[0]
        #                 measurement = Measurement(
        #                     id=msm_id,
        #                     target=target,
        #                     measurement_type=measurement_type,
        #                     status="pending",
        #                 )
        #                 self.repo.write_measurement(measurement, measurements_csv)
        #                 measurements_created += 1
        #                 counter += 1

        #                 logger.info(f"Created measurement {msm_id} for {target}")
                    
        #             # Rate limiting
        #             if counter >= self.rate_limit_count:
        #                 logger.info(f"Rate limit reached, sleeping for {self.rate_limit_sleep}s")
        #                 await asyncio.sleep(self.rate_limit_sleep)
        #                 counter = 0
                
        #         except Exception as e:
        #             logger.error(f"Error creating measurement for {target}: {e}")
        #             if e.response is not None and b"higher than your maximum daily results limit 100000" in e.response.content:
        #                 logger.error("Daily limit reached, stopping measurement creation.")
        #                 is_limit_exceed_error = True
                
        #         finally:
        #             logger.info(
        #                 "Measurement run summary | "
        #                 f"targets to process={len(targets_to_process)}, "
        #                 f"created={measurements_created}, "
        #                 f"remaining={len(targets_to_process) - measurements_created}, "
        #             )
        #             if is_limit_exceed_error:
        #                 api_key=self.get_api_key()
        #                 if api_key:
        #                     self.ripe_client = RipeAtlasClient(api_key)  # Switch to next API key
        #                     self.create_measurements(continent_code, measurement_type)  # Retry with new key
        #                 else:    
        #                     logger.info("Daily limit exceeded, sleeping for 24 hours.")
        #                     await asyncio.sleep(24 * 3600) # Sleep for 24 hours if daily limit is exceeded
                            
        
        for target in targets_to_process:
            # Create the measurement
            measurement_data = self._build_measurement_data(
                target, probe_ids_string, len(probes), measurement_type
            )
            
            try:
                #async with self.ripe_client as client:
                response = await self.ripe_client.create_measurement(target, measurement_data)
            
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
                    counter += 1

                    logger.info(f"Created measurement {msm_id} for {target}")
                
                # Rate limiting
                if counter >= self.rate_limit_count:
                    logger.info(f"Rate limit reached, sleeping for {self.rate_limit_sleep}s")
                    await asyncio.sleep(self.rate_limit_sleep)
                    counter = 0
        
            except Exception as e:
                logger.error(f"Error creating measurement for {target}: {e}")
                if e.response is not None and b"higher than your maximum daily results limit 100000" in e.response.content:
                    logger.error("Daily limit reached, stopping measurement creation.")
                    #is_limit_exceed_error = True
                    api_key=self.get_api_key()
                    if api_key:
                        await self.ripe_client.aclose()
                        self.ripe_client = RipeAtlasClient(api_key)  # Switch to next API key
                        #self.create_measurements(continent_code, measurement_type)  # Retry with new key
                    else:    
                        logger.info("No key left for today. Daily limit exceeded, sleeping for 24 hours.")
                        self.initialize_key_list()  # Reset keys for the next day
                        await asyncio.sleep(24 * 3600) # Sleep for 24 hours if daily limit is exceeded
                else:
                    logger.error(f"Unexpected error: {e}")
        
            logger.info(
                "Measurement run summary | "
                f"targets to process={len(targets_to_process)}, "
                f"created={measurements_created}, "
                f"remaining={len(targets_to_process) - measurements_created}, "
            )
                    
                    
        
        return {
            "status": "success",
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
    
    
    async def fetch_measurement_results(
        self,
        continent_code: str = "AF",
    ) -> AsyncGenerator[list[PingResult], None]:
        """Fetch results for all measurements that haven't been fetched yet."""
        
        measurements_csv = f"data/measurements/measurements_{continent_code.lower()}.csv"
        results_csv = f"data/measurements/measurement_details_{continent_code.lower()}.csv"

        all_measurements = self.repo.read_all_measurements(measurements_csv)
        already_fetched = self.repo.read_fetched_results(results_csv)
        
        measurements_to_fetch = [
            msm_id for msm_id in all_measurements.values()
            if msm_id not in already_fetched
        ]
        
        logger.info(f"Fetching results for {len(measurements_to_fetch)} measurements")
        
        total_saved = 0
        counter = 0
        async with RipeAtlasClient() as client:
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
                        
                        self.repo.write_ping_results(ping_results, results_csv)
                        total_saved += 1
                        logger.info(f"Saved {total_saved} results")
                    
                    counter += 1
                    if counter % 10 == 0:
                        await asyncio.sleep(10) #self.batch_sleep
                
                except Exception as e:
                    logger.error(f"Error fetching results for measurement {msm_id}: {e}")
        
        return {
            "status": "success",
            "message": f"Processed and saved {total_saved} results",
            "saved": total_saved,
            "planned": len(measurements_to_fetch),
            "remaining": len(measurements_to_fetch) - total_saved
        }
    
    # async def process_and_save_results(self, ripe_client) -> dict:
    #     """Process measurement results and save them."""
    #     total_saved = 0
        
    #     async for ping_results in self.fetch_measurement_results(ripe_client):
    #         if ping_results:
    #             self.repo.write_ping_results(ping_results)
    #             total_saved += len(ping_results)
    #             logger.info(f"Saved {len(ping_results)} results")
        
    #     return {
    #         "status": "success",
    #         "message": f"Processed and saved {total_saved} results",
    #         "saved": total_saved,
    #     }
    
    async def get_measurement_by_id(self, measurement_id: int, ripe_client) -> dict:
        """Get a specific measurement by ID."""
        async with ripe_client as client:
            response = await client.get_measurement(measurement_id)
            return response
    
    # ============================================
    # DATABASE OPERATIONS
    # ============================================
    
    async def get_measurement_for_target_analysis(self):
        """Get a measurement from the database."""
        if not self.repo.session:
            return None
        return await self.repo.get_measurements_for_target_analysis()
    
    
    
    
    async def create_measurement_in_db(self, measurement: Measurement) -> dict:
        """Create a measurement in the database."""
        if not self.repo.session:
            return {"status": "error", "message": "Database session not initialized"}
        return await self.repo.create_measurement(measurement)
    
    async def get_measurement_from_db(self, measurement_id: int) -> Optional[Measurement]:
        """Get a measurement from the database."""
        if not self.repo.session:
            return None
        return await self.repo.get_measurement(measurement_id)
    
    async def get_all_measurements_from_db(self) -> List[Measurement]:
        """Get all measurements from the database."""
        if not self.repo.session:
            return []
        return await self.repo.get_all_measurements()
    
    async def update_measurement_status_in_db(self, measurement_id: int, status: str) -> dict:
        """Update measurement status in the database."""
        if not self.repo.session:
            return {"status": "error", "message": "Database session not initialized"}
        return await self.repo.update_measurement_status(measurement_id, status)
    
    async def delete_measurement_from_db(self, measurement_id: int) -> dict:
        """Delete a measurement from the database."""
        if not self.repo.session:
            return {"status": "error", "message": "Database session not initialized"}
        return await self.repo.delete_measurement(measurement_id)