import os
import httpx

IP_INFO_BASE_URL = os.getenv("IP_INFO_BASE_URL")
IP_INFO_TOKEN = os.getenv("IP_INFO_TOKEN") ## put this in env for security

class IpinfoClient:
    """HTTPS client for ipinfo.io with Bearer token auth."""
    def __init__(self, token: str = IP_INFO_TOKEN, base_url: str = IP_INFO_BASE_URL, timeout: float = 8.0):
        base_url = os.getenv("IP_INFO_BASE_URL")
        token = os.getenv("IP_INFO_TOKEN") ## put this in env for security
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout,
            #http2=True,
        )

    async def lookup(self, ip: str):
        r = await self._client.get(f"/lite/{ip}")
        r.raise_for_status()
        return r.json()

    async def aclose(self): await self._client.aclose()
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): await self.aclose()