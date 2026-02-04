"""Anycast IP domain models."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class AnycastIP:
    """Represents an anycast IP address."""
    
    ip: str
    prefix: str
    num_sites: int
    
    @classmethod
    def from_dict(cls, data: dict) -> "AnycastIP":
        """Create AnycastIP from dictionary."""
        return cls(
            ip=data.get("ip", ""),
            prefix=data.get("prefix", ""),
            num_sites=data.get("num_sites", 0),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "ip": self.ip,
            "prefix": self.prefix,
            "num_sites": self.num_sites,
        }


@dataclass
class AnycastIPDetails:
    """Detailed information about an anycast IP."""
    
    ip_address: str
    asn: Optional[str] = None
    as_name: Optional[str] = None
    as_domain: Optional[str] = None
    as_org: Optional[str] = None
    country_code: Optional[str] = None
    country: Optional[str] = None
    continent: Optional[str] = None
    continent_code: Optional[str] = None
    
    @classmethod
    def from_ipinfo(cls, ip: str, ipinfo_data: dict) -> "AnycastIPDetails":
        """Create from IPInfo data."""
        return cls(
            ip_address=ip,
            asn=ipinfo_data.get("asn"),
            as_name=ipinfo_data.get("as_name"),
            as_domain=ipinfo_data.get("as_domain"),
            country_code=ipinfo_data.get("country_code"),
            country=ipinfo_data.get("country"),
            continent=ipinfo_data.get("continent"),
            continent_code=ipinfo_data.get("continent_code"),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV storage."""
        return {
            "ip_address": self.ip_address,
            "asn": self.asn,
            "as_name": self.as_name,
            "as_domain": self.as_domain,
            "as_org": self.as_org,
            "country_code": self.country_code,
            "country": self.country,
            "continent": self.continent,
            "continent_code": self.continent_code,
        }
