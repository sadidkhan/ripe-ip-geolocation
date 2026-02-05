"""Probe service with business logic."""
import logging
from typing import Optional
from repositories.probe_repository import ProbeRepository
from ripe_atlas_client import RipeAtlasClient

logger = logging.getLogger("ripe_atlas")


class ProbeService:
    """Business logic for probe operations."""
    
    def __init__(self):
        # self.african_probe_repo = african_probe_repository
        # self.african_countries = african_countries
        pass
    
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