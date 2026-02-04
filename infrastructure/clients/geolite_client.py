"""MaxMind GeoLite API client."""
import os
import httpx
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger("ripe_atlas")


@dataclass
class GeoLiteResult:
    """GeoLite query result."""
    ip_address: str
    as_num: Optional[int]
    as_org: Optional[str]
    network: Optional[str]
    continent: Optional[str]
    continent_code: Optional[str]
    country: Optional[str]
    country_iso: Optional[str]
    registered_country: Optional[str]
    registered_country_iso: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    time_zone: Optional[str]
    accuracy_radius_km: Optional[int]

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "GeoLiteResult":
        """Create from API response."""
        return cls(
            ip_address=data.get("traits", {}).get("ip_address"),
            as_num=data.get("traits", {}).get("autonomous_system_number"),
            as_org=data.get("traits", {}).get("autonomous_system_organization"),
            network=data.get("traits", {}).get("network"),
            continent=data.get("continent", {}).get("names", {}).get("en"),
            continent_code=data.get("continent", {}).get("code"),
            country=data.get("country", {}).get("names", {}).get("en"),
            country_iso=data.get("country", {}).get("iso_code"),
            registered_country=data.get("registered_country", {}).get("names", {}).get("en"),
            registered_country_iso=data.get("registered_country", {}).get("iso_code"),
            latitude=data.get("location", {}).get("latitude"),
            longitude=data.get("location", {}).get("longitude"),
            time_zone=data.get("location", {}).get("time_zone"),
            accuracy_radius_km=data.get("location", {}).get("accuracy_radius"),
        )


class GeoLiteClient:
    """HTTPS client for MaxMind GeoLite/GeoIP services. Uses Basic Auth."""

    def __init__(
        self,
        account_id: str = None,
        license_key: str = None,
        base_url: str = None,
        timeout: float = 8.0
    ):
        account_id = account_id or os.getenv("GEO_LITE_ACCOUNT_ID")
        license_key = license_key or os.getenv("GEO_LITE_LICENSE_KEY")
        base_url = base_url or os.getenv("GEO_LITE_BASE_URL")

        if not account_id or not license_key or not base_url:
            raise ValueError("GeoLite credentials and base URL are required")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            auth=(account_id, license_key),
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

    async def city(self, ip: str) -> Optional[GeoLiteResult]:
        """Get city-level geolocation for IP."""
        try:
            r = await self._client.get(f"/geoip/v2.1/city/{ip}?pretty")
            r.raise_for_status()
            data = r.json()
            return GeoLiteResult.from_response(data)
        except httpx.HTTPError as e:
            logger.error(f"Error fetching city data for {ip}: {e}")
            return None

    async def aclose(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
