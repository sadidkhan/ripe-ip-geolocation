"""Probe domain model."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Probe:
    """Represents a RIPE Atlas probe."""
    
    id: int
    country_code: str
    asn_v4: Optional[int] = None
    asn_v6: Optional[int] = None
    status: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address_v4: Optional[str] = None
    address_v6: Optional[str] = None
    prefix_v4: Optional[str] = None
    prefix_v6: Optional[str] = None
    is_anchor: bool = False
    is_public: bool = True
    
    @classmethod
    def from_dict(cls, data: dict) -> "Probe":
        """Create Probe from API response dict."""
        return cls(
            id=data.get("id"),
            country_code=data.get("country_code", ""),
            asn_v4=data.get("asn_v4"),
            asn_v6=data.get("asn_v6"),
            status=data.get("status"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            address_v4=data.get("address_v4"),
            address_v6=data.get("address_v6"),
            prefix_v4=data.get("prefix_v4"),
            prefix_v6=data.get("prefix_v6"),
            is_anchor=data.get("is_anchor", False),
            is_public=data.get("is_public", True),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV storage."""
        return {
            "id": self.id,
            "country_code": self.country_code,
            "asn_v4": self.asn_v4,
            "asn_v6": self.asn_v6,
            "status": self.status,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address_v4": self.address_v4,
            "address_v6": self.address_v6,
            "prefix_v4": self.prefix_v4,
            "prefix_v6": self.prefix_v6,
            "is_anchor": self.is_anchor,
            "is_public": self.is_public,
        }
    
    def is_african(self, african_countries: set[str]) -> bool:
        """Check if probe is in an African country."""
        return self.country_code in african_countries