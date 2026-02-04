"""API dependencies for dependency injection."""
from functools import lru_cache
from config import get_settings
from domain.services import ProbeService, MeasurementService, AnycastService
from infrastructure.clients import RipeAtlasClient, IpinfoClient, GeoLiteClient
from infrastructure.repositories import ProbeRepository, MeasurementRepository, AnycastRepository


@lru_cache()
def get_probe_service() -> ProbeService:
    """Get ProbeService instance."""
    settings = get_settings()
    
    probe_repo = ProbeRepository(settings.all_probes_csv)
    african_probe_repo = ProbeRepository(settings.african_probes_csv)
    
    return ProbeService(
        probe_repository=probe_repo,
        african_probe_repository=african_probe_repo,
        african_countries=settings.african_countries,
    )


@lru_cache()
def get_measurement_service() -> MeasurementService:
    """Get MeasurementService instance."""
    settings = get_settings()
    
    measurement_repo = MeasurementRepository(
        measurements_csv=settings.measurements_csv,
        failed_csv=settings.failed_measurements_csv,
        results_csv=settings.ping_results_csv,
    )
    
    return MeasurementService(
        measurement_repository=measurement_repo,
        rate_limit_count=settings.measurement_rate_limit_count,
        rate_limit_sleep=settings.measurement_rate_limit_sleep_seconds,
        batch_sleep=settings.measurement_result_batch_sleep_seconds,
    )


@lru_cache()
def get_anycast_service() -> AnycastService:
    """Get AnycastService instance."""
    settings = get_settings()
    
    anycast_repo = AnycastRepository(
        ip_list_csv=settings.anycast_ip_list_csv,
        ip_details_csv=settings.anycast_ip_details_csv,
    )
    
    return AnycastService(
        anycast_repository=anycast_repo,
        hitlist_fsdb_path=str(settings.anycast_hitlist_fsdb),
        batch_size=settings.measurement_batch_size,
    )


def get_ripe_atlas_client() -> RipeAtlasClient:
    """Get RipeAtlasClient instance."""
    settings = get_settings()
    return RipeAtlasClient(
        api_key=settings.ripe_atlas_api_key,
        base_url=settings.ripe_atlas_base_url,
    )


def get_ipinfo_client() -> IpinfoClient:
    """Get IpinfoClient instance."""
    settings = get_settings()
    return IpinfoClient(
        token=settings.ipinfo_token,
    )


def get_geolite_client() -> GeoLiteClient:
    """Get GeoLiteClient instance."""
    settings = get_settings()
    return GeoLiteClient()
