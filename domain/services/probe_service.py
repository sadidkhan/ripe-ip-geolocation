"""Probe service with business logic."""
import logging
from typing import Optional
from domain.models import Probe
from infrastructure.repositories import ProbeRepository

logger = logging.getLogger("ripe_atlas")


class ProbeService:
    """Business logic for probe operations."""
    
    def __init__(
        self,
        probe_repository: ProbeRepository,
        african_probe_repository: ProbeRepository,
        african_countries: frozenset[str],
    ):
        self.probe_repo = probe_repository
        self.african_probe_repo = african_probe_repository
        self.african_countries = african_countries
    
    async def get_all_probes(self, ripe_client) -> list[Probe]:
        """Get all probes, fetching from API if not cached."""
        # Try to load from cache first
        if self.probe_repo.exists():
            logger.info("Loading probes from cache")
            return self.probe_repo.read_all()
        
        # Fetch from API
        logger.info("Fetching probes from RIPE Atlas API")
        probes = []
        async with ripe_client as client:
            async for probe_data in client.get_probes():
                probes.append(Probe.from_dict(probe_data))
        
        # Cache the results
        self.probe_repo.write_all(probes)
        logger.info(f"Cached {len(probes)} probes")
        
        return probes
    
    async def get_african_probes(self, ripe_client) -> list[Probe]:
        """Get African probes, fetching if not cached."""
        # Try to load from cache first
        if self.african_probe_repo.exists():
            logger.info("Loading African probes from cache")
            return self.african_probe_repo.read_all()
        
        # Get all probes and filter
        logger.info("Filtering African probes")
        all_probes = await self.get_all_probes(ripe_client)
        african_probes = [
            probe for probe in all_probes
            if probe.is_african(self.african_countries)
        ]
        
        # Cache the results
        self.african_probe_repo.write_all(african_probes)
        logger.info(f"Cached {len(african_probes)} African probes")
        
        return african_probes
    
    def get_probe_ids_string(self, probes: list[Probe]) -> str:
        """Convert probe list to comma-separated ID string for RIPE Atlas API."""
        return ",".join(str(probe.id) for probe in probes)
