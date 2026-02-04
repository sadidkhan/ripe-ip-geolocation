"""RIPE Atlas API client."""
import os
import httpx
import logging

logger = logging.getLogger("ripe_atlas")


class RipeAtlasClient:
    """HTTPS client for RIPE Atlas API with API key auth."""

    def __init__(self, api_key: str = None, base_url: str = None, timeout: float = 10.0):
        api_key = api_key or os.getenv("RIPE_ATLAS_API_KEY")
        base_url = base_url or os.getenv("RIPE_ATLAS_BASE_URL") or "https://atlas.ripe.net/api/v2/"

        if not api_key:
            raise ValueError("RIPE Atlas API key is required")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Key {api_key}", "Accept": "application/json"},
            timeout=timeout,
        )

    async def get_probes(self, status: int = 1, page_size: int = 1000):
        """Fetch all probes with pagination."""
        url = f"/probes/?status={status}&page_size={page_size}"
        while url:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for probe in data.get("results", []):
                yield probe
            url = data.get("next")

    async def create_measurement(self, target: str, measurement_data: dict = None):
        """Create a new measurement."""
        try:
            resp = await self._client.post("/measurements/", json=measurement_data)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to create measurement for {target}: {e}")
            raise e

    async def get_measurement_result(self, measurement_id: int):
        """Get measurement results by ID."""
        try:
            resp = await self._client.get(f"/measurements/{measurement_id}/results/")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching measurement {measurement_id}: {e}")
            if hasattr(e, 'response'):
                logger.error(f"Details: {e.response.content}")
            return []

    async def get_measurement(self, measurement_id: int):
        """Get measurement metadata by ID."""
        try:
            resp = await self._client.get(f"/measurements/{measurement_id}/")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching measurement {measurement_id}: {e}")
            if hasattr(e, 'response'):
                logger.error(f"Details: {e.response.content}")
            return {}

    async def aclose(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
