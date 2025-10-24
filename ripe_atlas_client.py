# atlas_client.py
import os
import httpx

RIPE_ATLAS_BASE_URL = os.getenv("RIPE_ATLAS_BASE_URL", "https://atlas.ripe.net/api/v2/")
RIPE_ATLAS_API_KEY = os.getenv("RIPE_ATLAS_API_KEY")  # store securely in env

import logging
logger = logging.getLogger("ripe_atlas")

class RipeAtlasClient:

    
    """HTTPS client for RIPE Atlas API with API key auth."""

    def __init__(self, api_key: str = RIPE_ATLAS_API_KEY, base_url: str = RIPE_ATLAS_BASE_URL, timeout: float = 10.0):
        api_key = api_key or os.getenv("RIPE_ATLAS_API_KEY")
        base_url = base_url or os.getenv("RIPE_ATLAS_BASE_URL") or "https://atlas.ripe.net/api/v2/"

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Key {api_key}", "Accept": "application/json"},
            timeout=timeout,
        )

    async def get_probes(self, status: int = 1, page_size: int = 1000):
        url = f"/probes/?status={status}&page_size={page_size}"
        while url:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for probe in data.get("results", []):
                yield probe
            url = data.get("next")

    
    async def create_measurement(self, target, measurement_data: dict = None):
        try:
            resp = await self._client.post("/measurements/", json=measurement_data)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Error while creating measurement for {target}: error: {e}")
            return None
        
    
    async def get_measurement(self, id):
        try:
            resp = await self._client.get(f"/measurements/{id}/results/")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Error while fetching measurement {id}: error: {e}")
            logger.error(f"details: {e.response.content}")
            return []
    


    async def aclose(self): await self._client.aclose()
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): await self.aclose()
