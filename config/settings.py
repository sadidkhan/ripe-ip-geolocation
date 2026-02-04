"""Application settings using Pydantic."""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import FrozenSet


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    ripe_atlas_api_key: str
    ipinfo_token: str | None = None
    geolite_db_path: str | None = None
    
    # RIPE Atlas
    ripe_atlas_base_url: str = "https://atlas.ripe.net/api/v2/"
    
    # Data paths
    data_dir: Path = Path("data")
    probe_data_dir: Path = Path("data/ripe")
    measurement_data_dir: Path = Path("data/measurements")
    anycast_data_dir: Path = Path("data/anycast")
    ipinfo_data_dir: Path = Path("data/ipinfo")
    
    # File paths
    all_probes_csv: Path = Path("data/ripe/all_active_probes.csv")
    african_probes_csv: Path = Path("data/ripe/african_active_probes.csv")
    measurements_csv: Path = Path("data/measurements/measurements.csv")
    failed_measurements_csv: Path = Path("data/measurements/failed.csv")
    ping_results_csv: Path = Path("data/measurements/ping_result_fixed3.csv")
    anycast_ip_list_csv: Path = Path("data/anycast/anycast_ip_list.csv")
    anycast_ip_details_csv: Path = Path("data/anycast/anycast_ip_details.csv")
    anycast_hitlist_fsdb: Path = Path("data/anycast/internet_address_hitlist_it113w-20250827.fsdb")
    
    # African countries
    african_countries: FrozenSet[str] = frozenset({
        "DZ", "AO", "BJ", "BW", "BF", "BI", "CM", "CV", "CF", "TD", "KM",
        "CD", "CG", "CI", "DJ", "EG", "GQ", "ER", "SZ", "ET", "GA", "GM",
        "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG", "MW", "ML", "MR",
        "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN", "SC", "SL",
        "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "ZM", "ZW"
    })
    
    # Measurement settings
    measurement_batch_size: int = 10
    measurement_rate_limit_count: int = 90
    measurement_rate_limit_sleep_seconds: int = 800
    measurement_result_batch_sleep_seconds: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
