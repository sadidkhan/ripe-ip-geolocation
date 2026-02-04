"""Anycast IP service with business logic."""
import logging
import pandas as pd
from typing import Optional
from domain.models import AnycastIP, AnycastIPDetails
from infrastructure.repositories import AnycastRepository

logger = logging.getLogger("ripe_atlas")


class AnycastService:
    """Business logic for anycast IP operations."""
    
    def __init__(
        self,
        anycast_repository: AnycastRepository,
        hitlist_fsdb_path: str,
        batch_size: int = 10,
    ):
        self.repo = anycast_repository
        self.hitlist_fsdb_path = hitlist_fsdb_path
        self.batch_size = batch_size
    
    def get_anycast_ips(self, date_str: str = "2025/10/08", min_sites: int = 0) -> list[str]:
        """Get list of anycast IPs, using cache if available."""
        # Try cache first
        if self.repo.ip_list_exists():
            logger.info("Loading anycast IPs from cache")
            return self.repo.read_ip_list()
        
        # Build from anycast census and hitlist
        logger.info("Building anycast IP list from census and hitlist")
        anycast_dict = self._build_anycast_dict(date_str, min_sites)
        matched_ips = self._match_with_hitlist(anycast_dict)
        
        # Cache the results
        self.repo.write_ip_list(matched_ips)
        logger.info(f"Cached {len(matched_ips)} anycast IPs")
        
        return matched_ips
    
    def _build_anycast_dict(self, date_str: str, min_sites: int) -> dict:
        """Build dictionary of anycast prefixes from census data."""
        base_url = "https://raw.githubusercontent.com/ut-dacs/anycast-census/main/"
        csv_url = f"{base_url}{date_str}/IPv4.csv"
        
        # Load and filter
        df = pd.read_csv(csv_url)
        filtered = df[df["number_of_sites"] > min_sites].sort_values(
            by="number_of_sites", ascending=False
        )
        
        # Build dict with first 3 octets as key
        anycast_dict = {}
        for _, row in filtered.iterrows():
            prefix = row["prefix"]
            num_sites = row["number_of_sites"]
            try:
                base = ".".join(prefix.split(".")[:3])
                anycast_dict[base] = {
                    "prefix": prefix,
                    "num_sites": num_sites,
                }
            except Exception as e:
                logger.error(f"Error processing prefix {prefix}: {e}")
        
        return anycast_dict
    
    def _match_with_hitlist(self, anycast_dict: dict) -> list[str]:
        """Match anycast prefixes with IPs from FSDB hitlist."""
        matched_ips = []
        
        with open(self.hitlist_fsdb_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split()
                try:
                    score = int(parts[1])
                    if score > 0:
                        ip = parts[2]
                        base = ".".join(ip.split(".")[:3])
                        if base in anycast_dict:
                            anycast_dict[base]["ip"] = ip
                            matched_ips.append(ip)
                except (ValueError, IndexError):
                    continue
        
        return matched_ips
    
    async def enrich_anycast_ips(
        self,
        ips: Optional[list[str]] = None,
        ipinfo_client = None,
        geolite_client = None,
    ) -> dict:
        """Enrich anycast IPs with geolocation data."""
        if ips is None:
            ips = self.get_anycast_ips()
        
        # Check which IPs are already enriched
        existing_ips = self.repo.read_existing_ip_addresses()
        new_ips = [ip for ip in ips if ip not in existing_ips]
        
        if not new_ips:
            logger.info(f"All {len(ips)} IPs already enriched")
            return {
                "status": "complete",
                "seen": len(ips),
                "skipped": len(existing_ips),
                "written": 0,
                "errors": 0,
            }
        
        logger.info(f"Enriching {len(new_ips)} new IPs")
        
        written = 0
        errors = 0
        details_list = []
        
        # Process in batches
        for batch_start in range(0, len(new_ips), self.batch_size):
            batch = new_ips[batch_start:batch_start + self.batch_size]
            logger.info(f"Processing batch {batch_start // self.batch_size + 1}")
            
            for ip in batch:
                try:
                    # Fetch IPInfo data
                    ipinfo_data = await ipinfo_client.lookup(ip)
                    
                    if not ipinfo_data:
                        logger.warning(f"No data for {ip}")
                        errors += 1
                        continue
                    
                    # Create domain model
                    details = AnycastIPDetails.from_ipinfo(ip, ipinfo_data)
                    details_list.append(details)
                    written += 1
                    
                except Exception as e:
                    logger.error(f"Error enriching {ip}: {e}")
                    errors += 1
            
            # Write batch to CSV
            if details_list:
                self.repo.write_ip_details(details_list, append=True)
                details_list = []
        
        return {
            "status": "success",
            "seen": len(ips),
            "skipped": len(existing_ips),
            "written": written,
            "errors": errors,
        }
