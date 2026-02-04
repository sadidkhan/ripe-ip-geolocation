"""IPInfo API client."""
import os
import httpx
import logging

logger = logging.getLogger("ripe_atlas")


class IpinfoClient:
    """HTTPS client for ipinfo.io with Bearer token auth."""

    def __init__(self, token: str = None, base_url: str = None, timeout: float = 8.0):
        token = token or os.getenv("IP_INFO_TOKEN")
        base_url = base_url or os.getenv("IP_INFO_BASE_URL")

        if not token or not base_url:
            raise ValueError("IPInfo token and base URL are required")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
        )

    async def lookup(self, ip: str) -> dict:
        """Look up IP address information."""
        try:
            r = await self._client.get(f"/lite/{ip}")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            logger.error(f"Error looking up IP {ip}: {e}")
            return {}

    async def aclose(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
