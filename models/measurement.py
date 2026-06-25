"""Measurement domain models."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

from sqlalchemy import BigInteger, Float, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


@dataclass
class Measurement:
    """Represents a RIPE Atlas measurement."""
    
    id: int
    target: str
    measurement_type: Literal["ping", "traceroute"]
    status: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Measurement":
        """Create Measurement from API response dict."""
        created = data.get("created")
        created_dt = datetime.fromtimestamp(created) if created else None
        
        return cls(
            id=data.get("id"),
            target=data.get("target", ""),
            measurement_type=data.get("type", "ping"),
            status=data.get("status", {}).get("name", "unknown"),
            created_at=created_dt,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV storage."""
        return {
            "measurement_id": self.id,
            "target": self.target,
        }


@dataclass
class PingResult:
    """Represents a single ping result from a probe."""
    
    measurement_id: int
    probe_id: int
    target: str
    source_address: str
    timestamp: int
    sent: int
    received: int
    loss_percentage: float
    continent_code: str
    continent_id: Optional[int] = None
    min_rtt: Optional[float] = None
    avg_rtt: Optional[float] = None
    max_rtt: Optional[float] = None
    rtt1: Optional[float] = None
    rtt2: Optional[float] = None
    rtt3: Optional[float] = None
    
    @property
    def timestamp_iso(self) -> str:
        """Get ISO formatted timestamp."""
        return datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else ""
    
    @classmethod
    def from_api_response(cls, data: dict, continent_code: str, continent_id: Optional[int] = None) -> "PingResult":
        """Create PingResult from RIPE Atlas API response.
        
        Args:
            data: API response data
            continent_code: 2-character continent code (AF, SA, NA, etc.)
            continent_id: Optional continent ID for the probe
        """
        rtts = [pkt.get("rtt") for pkt in data.get("result", []) if pkt.get("rtt") is not None]
        rtts += [None] * (3 - len(rtts))  # Pad to 3 RTTs
        
        sent = data.get("sent", 0)
        rcvd = data.get("rcvd", 0)
        loss_pct = round(100.0 * (max(sent - rcvd, 0)) / sent, 2) if sent else 0.0
        
        return cls(
            measurement_id=data.get("msm_id") or data.get("group_id"),
            probe_id=data.get("prb_id"),
            target=data.get("dst_addr") or data.get("dst_name"),
            source_address=data.get("from") or data.get("src_addr"),
            timestamp=data.get("timestamp"),
            sent=sent,
            received=rcvd,
            loss_percentage=loss_pct,
            continent_code=continent_code,
            continent_id=continent_id,
            min_rtt=data.get("min"),
            avg_rtt=data.get("avg"),
            max_rtt=data.get("max"),
            rtt1=rtts[0],
            rtt2=rtts[1],
            rtt3=rtts[2],
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV storage."""
        return {
            "measurement_id": self.measurement_id,
            "probe_id": self.probe_id,
            "dst_addr": self.target,
            "from": self.source_address,
            "timestamp_unix": self.timestamp,
            "timestamp_iso": self.timestamp_iso,
            "sent": self.sent,
            "rcvd": self.received,
            "loss_pct": self.loss_percentage,
            "min_ms": self.min_rtt,
            "avg_ms": self.avg_rtt,
            "max_ms": self.max_rtt,
            "rtt1": self.rtt1,
            "rtt2": self.rtt2,
            "rtt3": self.rtt3,
        }

    def to_db_dict(self, serial_no: Optional[int] = None) -> dict:
        """Convert ping result to a dictionary suitable for DB insertion.
        
        Args:
            serial_no: Optional serial number for this result in batch
        """
        return {
            "serial_no": serial_no,
            "measurement_id": self.measurement_id,
            "probe_id": self.probe_id,
            "dst_addr": self.target,
            "src_addr": self.source_address,
            "timestamp_unix": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp) if self.timestamp else None,
            "sent": self.sent,
            "rcvd": self.received,
            "loss_pct": self.loss_percentage,
            "min_ms": self.min_rtt,
            "avg_ms": self.avg_rtt,
            "max_ms": self.max_rtt,
            "rtt1": self.rtt1,
            "rtt2": self.rtt2,
            "rtt3": self.rtt3,
            "continent_code": self.continent_code,
            "continent_id": self.continent_id,
        }


class PingResultDB(Base):
    """ORM mapping for ping results stored in the measurements table."""
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    serial_no: Mapped[Optional[int]] = mapped_column(Integer)
    measurement_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    probe_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dst_addr: Mapped[Optional[str]] = mapped_column(INET)
    src_addr: Mapped[Optional[str]] = mapped_column(INET)
    timestamp_unix: Mapped[Optional[int]] = mapped_column(BigInteger)
    timestamp_iso: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    sent: Mapped[Optional[int]] = mapped_column(Integer)
    rcvd: Mapped[Optional[int]] = mapped_column(Integer)
    loss_pct: Mapped[Optional[float]] = mapped_column(Float)
    min_ms: Mapped[Optional[float]] = mapped_column(Float)
    avg_ms: Mapped[Optional[float]] = mapped_column(Float)
    max_ms: Mapped[Optional[float]] = mapped_column(Float)
    rtt1: Mapped[Optional[float]] = mapped_column(Float)
    rtt2: Mapped[Optional[float]] = mapped_column(Float)
    rtt3: Mapped[Optional[float]] = mapped_column(Float)
    continent_code: Mapped[str] = mapped_column(String(10), nullable=False)
    continent_id: Mapped[Optional[int]] = mapped_column(Integer)


@dataclass
class MeasurementResult:
    """Aggregate result for a measurement."""
    
    measurement_id: int
    target: str
    probe_results: list[PingResult] = field(default_factory=list)
    
    @property
    def total_probes(self) -> int:
        """Total number of probes."""
        return len(self.probe_results)
    
    @property
    def successful_probes(self) -> int:
        """Number of probes with at least one response."""
        return sum(1 for pr in self.probe_results if pr.received > 0)