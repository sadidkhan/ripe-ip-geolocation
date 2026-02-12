"""Probe service with business logic."""
import logging
from typing import Any, Dict, List, Tuple, Optional
from repositories.probe_repository import ProbeRepository
from ripe_atlas_client import RipeAtlasClient
from collections import defaultdict
from models.probe import Probe

logger = logging.getLogger("ripe_atlas")


class ProbeService:
    """Business logic for probe operations."""
    
    def __init__(self, probe_repository: Optional[ProbeRepository] = None):
        """Initialize ProbeService with optional repository for database operations."""
        self.repo = probe_repository
    
    async def fetch_all_probes(self):
        probes = []
        async with RipeAtlasClient() as client:
            async for probe in client.get_probes():
                probes.append(probe)
        return probes
    
    async def get_all_probes(self):
        """Get all probes, fetching from API if not cached."""
        # Try to load from cache first
        
        probe_repo = ProbeRepository("data/ripe/all_active_probes_v2.csv")
        
        if probe_repo.exists():
            logger.info("Loading probes from File")
            return probe_repo.read_probes_from_csv()
        
        # Fetch from API
        logger.info("Fetching probes from RIPE Atlas API")
        probes = await self.fetch_all_probes()
        
        # Cache the results
        probe_repo.write_probes_to_csv(probes)
        logger.info(f"Cached {len(probes)} probes")
        
        return probes
    
    async def get_filtered_probes(self, continent_code: str):
        probes = await self.get_continent_probes(continent_code)
        filtered_probes = self.filter_max_two_probes_per_country_asn(probes)
        logger.info(f"continent_code: {continent_code}, total_continent_probes: {len(probes)}, filtered_probes: {len(filtered_probes)}")
        return filtered_probes
    
    async def get_continent_probes(self, continent_code: str):
        settings = self.getSettings(continent_code)
        probe_repo = ProbeRepository(settings["probe_file_path"])
        
        if probe_repo.exists():
            logger.info(f"Loading {settings['continent']} probes from File")
            return probe_repo.read_probes_from_csv()
        
        # Get all probes and filter
        logger.info(f"Filtering {settings['continent']} probes")
        all_probes = await self.get_all_probes()
        continent_probes = [
            probe for probe in all_probes 
            if probe.get("country_code") in settings["county_codes"]]
        
        # Cache the results
        probe_repo.write_probes_to_csv(continent_probes)
        logger.info(f"Cached {len(continent_probes)} {settings['continent']} probes")
        
        return continent_probes
    

    def filter_max_two_probes_per_country_asn(
        self,
        probes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Keep at most 2 probes per (country_code, asn_v4).

        Ranking rule (best first):
        1) last_connected (desc)
        2) total_uptime (desc)
        3) id (asc)  # stable
        """
        def as_int(v, default=0):
            try:
                return int(v)
            except Exception:
                return default

        buckets: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)

        for p in probes:
            cc = p.get("country_code")
            asn = p.get("asn_v4")
            if not cc or asn is None:
                continue

            asn_i = as_int(asn, -1)
            if asn_i == -1:
                continue

            buckets[(cc, asn_i)].append(p)

        selected: List[Dict[str, Any]] = []
        for (_cc, _asn), items in buckets.items():
            items_sorted = sorted(
                items,
                key=lambda x: (
                    -as_int(x.get("last_connected"), 0),
                    -as_int(x.get("total_uptime"), 0),
                    as_int(x.get("id"), 10**18),
                ),
            )
            selected.extend(items_sorted[:1])

        return selected

    
    def getSettings(self, continent_code: str = "AF") -> dict:
        
        AFRICAN_COUNTRIES: frozenset[str] = frozenset({
            "DZ","AO","BJ","BW","BF","BI","CM","CV","CF","TD","KM",
            "CD","CG","CI","DJ","EG","GQ","ER","SZ","ET","GA","GM",
            "GH","GN","GW","KE","LS","LR","LY","MG","MW","ML","MR",
            "MU","MA","MZ","NA","NE","NG","RW","ST","SN","SC","SL",
            "SO","ZA","SS","SD","TZ","TG","TN","UG","ZM","ZW"
        })
        
        SOUTH_AMERICA_COUNTRIES: frozenset[str] = frozenset({
            "AR","BO","BR","CL","CO","EC","FK","GF","GY",
            "PE","PY","SR","UY","VE"
        })
        
        settings = {
            "AF": {
                "continent": "Africa", 
                "probe_file_path": "data/ripe/african_active_probes.csv",
                "county_codes": AFRICAN_COUNTRIES},
            "SA": {
                "continent": "South America", 
                "probe_file_path": "data/ripe/south_american_active_probes.csv",
                "county_codes": SOUTH_AMERICA_COUNTRIES}
        }
        
        return settings.get(continent_code, settings["AF"])
    
    # async def get_all_probes(self, ripe_client) -> list[Probe]:
    #     """Get all probes, fetching from API if not cached."""
    #     # Try to load from cache first
    #     if self.probe_repo.exists():
    #         logger.info("Loading probes from File")
    #         return self.probe_repo.read_probes_from_csv()
        
    #     # Fetch from API
    #     logger.info("Fetching probes from RIPE Atlas API")
    #     probes = []
    #     async with ripe_client as client:
    #         async for probe_data in client.get_probes():
    #             probes.append(Probe.from_dict(probe_data))
        
    #     # Cache the results
    #     self.probe_repo.write_probes_to_csv(probes)
    #     logger.info(f"Cached {len(probes)} probes")
        
    #     return probes
    
    # async def get_african_probes(self, ripe_client) -> list[Probe]:
    #     """Get African probes, fetching if not cached."""
    #     # Try to load from cache first
    #     if self.african_probe_repo.exists():
    #         logger.info("Loading African probes from cache")
    #         return self.african_probe_repo.read_all()
        
    #     # Get all probes and filter
    #     logger.info("Filtering African probes")
    #     all_probes = await self.get_all_probes(ripe_client)
    #     african_probes = [
    #         probe for probe in all_probes
    #         if probe.is_african(self.african_countries)
    #     ]
        
    #     # Cache the results
    #     self.african_probe_repo.write_all(african_probes)
    #     logger.info(f"Cached {len(african_probes)} African probes")
        
    #     return african_probes
    
    # def get_probe_ids_string(self, probes: list[Probe]) -> str:
    #     """Convert probe list to comma-separated ID string for RIPE Atlas API."""
    #     return ",".join(str(probe.id) for probe in probes)
    
    # ============================================
    # DATABASE OPERATIONS
    # ============================================
    
    async def create_probe_in_db(self, probe: Probe) -> dict:
        """Create a probe in the database."""
        if not self.repo:
            return {"status": "error", "message": "Repository not initialized"}
        return await self.repo.create_probe(probe)
    
    async def get_probe_from_db(self, probe_id: int) -> Optional[Probe]:
        """Get a probe from the database."""
        if not self.repo:
            return None
        return await self.repo.get_probe(probe_id)
    
    async def get_all_probes_from_db(self) -> List[Probe]:
        """Get all probes from the database."""
        if not self.repo:
            return []
        return await self.repo.get_all_probes()
    
    async def get_probes_by_country_from_db(self, country_code: str) -> List[Probe]:
        """Get all probes for a specific country from the database."""
        if not self.repo:
            return []
        return await self.repo.get_probes_by_country(country_code)
    
    async def delete_probe_from_db(self, probe_id: int) -> dict:
        """Delete a probe from the database."""
        if not self.repo:
            return {"status": "error", "message": "Repository not initialized"}
        return await self.repo.delete_probe(probe_id)