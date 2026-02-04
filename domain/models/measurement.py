"""Measurement domain models."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal


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
    def from_api_response(cls, data: dict) -> "PingResult":
        """Create PingResult from RIPE Atlas API response."""
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
