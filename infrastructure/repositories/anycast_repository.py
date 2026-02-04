"""Anycast IP repository for data persistence."""
import csv
import os
from pathlib import Path
from typing import Optional
from domain.models import AnycastIP, AnycastIPDetails


class AnycastRepository:
    """Handles anycast IP data persistence to CSV."""
    
    def __init__(self, ip_list_csv: Path, ip_details_csv: Path):
        self.ip_list_csv = ip_list_csv
        self.ip_details_csv = ip_details_csv
    
    def read_ip_list(self) -> list[str]:
        """Read list of anycast IPs from CSV."""
        if not os.path.exists(self.ip_list_csv):
            return []
        
        ips = []
        with open(self.ip_list_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ips.append(row["ip"])
        return ips
    
    def write_ip_list(self, ips: list[str]) -> None:
        """Write list of anycast IPs to CSV."""
        os.makedirs(os.path.dirname(self.ip_list_csv), exist_ok=True)
        
        with open(self.ip_list_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ip"])
            for ip in ips:
                writer.writerow([ip])
    
    def read_ip_details(self) -> list[AnycastIPDetails]:
        """Read detailed anycast IP information from CSV."""
        if not os.path.exists(self.ip_details_csv):
            return []
        
        details = []
        with open(self.ip_details_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                detail = AnycastIPDetails(
                    ip_address=row.get("ip_address", ""),
                    asn=row.get("asn"),
                    as_name=row.get("as_name"),
                    as_domain=row.get("as_domain"),
                    as_org=row.get("as_org"),
                    country_code=row.get("country_code"),
                    country=row.get("country"),
                    continent=row.get("continent"),
                    continent_code=row.get("continent_code"),
                )
                details.append(detail)
        return details
    
    def read_existing_ip_addresses(self) -> set[str]:
        """Read existing IP addresses to avoid duplicates."""
        if not os.path.exists(self.ip_details_csv) or os.path.getsize(self.ip_details_csv) == 0:
            return set()
        
        existing = set()
        with open(self.ip_details_csv, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = row.get("ip_address")
                if ip:
                    existing.add(ip)
        return existing
    
    def write_ip_details(self, details: list[AnycastIPDetails], append: bool = True) -> None:
        """Write detailed anycast IP information to CSV."""
        if not details:
            return
        
        os.makedirs(os.path.dirname(self.ip_details_csv), exist_ok=True)
        
        fieldnames = [
            "ip_address", "asn", "as_name", "as_domain", "as_org",
            "country_code", "country", "continent", "continent_code"
        ]
        
        mode = "a" if append and os.path.exists(self.ip_details_csv) else "w"
        header_needed = mode == "w" or not os.path.exists(self.ip_details_csv) or os.path.getsize(self.ip_details_csv) == 0
        
        with open(self.ip_details_csv, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if header_needed:
                writer.writeheader()
            writer.writerows([detail.to_dict() for detail in details])
    
    def ip_list_exists(self) -> bool:
        """Check if IP list file exists and is not empty."""
        return os.path.exists(self.ip_list_csv) and os.path.getsize(self.ip_list_csv) > 0
