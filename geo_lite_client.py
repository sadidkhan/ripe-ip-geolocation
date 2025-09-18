import os
import httpx

GEO_LITE_BASE_URL = os.getenv("GEO_LITE_BASE_URL")
GEO_LITE_ACCOUNT_ID = os.getenv("GEO_LITE_ACCOUNT_ID")
GEO_LITE_LICENSE_KEY = os.getenv("GEO_LITE_LICENSE_KEY") ## put this in env for security

class GeoLiteClient:
    """
    HTTPS client for MaxMind GeoLite/GeoIP services.
    Uses Basic Auth: username=Account ID, password=License Key.
    """
    def __init__(self, account_id: str = GEO_LITE_ACCOUNT_ID, license_key: str = GEO_LITE_LICENSE_KEY,
                 base_url: str = GEO_LITE_BASE_URL, timeout: float = 8.0):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            auth=(account_id, license_key),
            headers={"Accept": "application/json"},
            timeout=timeout,
            #http2=True,
        )

    async def city(self, ip: str):
        try:
            r = await self._client.get(f"/geoip/v2.1/city/{ip}?pretty")
            r.raise_for_status()
            data = r.json()
            return GeoLiteResult.from_response(data)
        except httpx.HTTPError as e:
            print(f"Error fetching city data for {ip}: {e}")
            return None         

    async def aclose(self): await self._client.aclose()
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): await self.aclose()



# Data model for GeoLite response
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class GeoLiteResult:
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
