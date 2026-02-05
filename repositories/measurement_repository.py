"""Measurement repository for data persistence."""
import csv
import os
from pathlib import Path
from models import Measurement
from models.measurement import PingResult


class MeasurementRepository:
    """Handles measurement data persistence to CSV."""
    
    def __init__(self):
        pass
     
    
    def read_all_measurements(self, measurements_csv: Path) -> dict[str, int]:
        """Read all measurements from CSV. Returns dict of {target: measurement_id}."""
        if not os.path.exists(measurements_csv):
            return {}
        
        measurements = {}
        with open(measurements_csv, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                target = row.get('target')
                measurement_id = row.get('measurement_id')
                if target and measurement_id:
                    measurements[target.strip()] = int(measurement_id.strip())
        return measurements
    
    def write_measurement(self, measurement: Measurement, measurements_csv: Path) -> None:
        """Write a single measurement to CSV."""
        os.makedirs(os.path.dirname(measurements_csv), exist_ok=True)
        new_file = not os.path.exists(measurements_csv)
        
        with open(measurements_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["target", "measurement_id"])
            writer.writerow([measurement.target, measurement.id])
    
    # def write_failed_measurement(self, target: str, error: str) -> None:
    #     """Write a failed measurement to CSV."""
    #     os.makedirs(os.path.dirname(self.failed_csv), exist_ok=True)
    #     new_file = not os.path.exists(self.failed_csv)
        
    #     # Sanitize error message
    #     error = (error or "").strip().replace("\n", " ")[:500]
        
    #     with open(self.failed_csv, "a", newline="", encoding="utf-8") as f:
    #         writer = csv.writer(f)
    #         if new_file:
    #             writer.writerow(["target", "timestamp", "error"])
    #         writer.writerow([target, datetime.now().isoformat(timespec="seconds"), error])
    
    def read_fetched_results(self, results_csv: Path) -> set[int]:
        """Read measurement IDs that have already been fetched."""
        if not os.path.isfile(results_csv):
            return set()
        
        measurement_ids = set()
        with open(results_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                msm_id = row.get("measurement_id")
                if msm_id:
                    try:
                        measurement_ids.add(int(msm_id))
                    except ValueError:
                        continue
        return measurement_ids
    
    def write_ping_results(self, results: list[PingResult], results_csv: Path) -> None:
        """Write ping results to CSV."""
        if not results:
            return
        
        os.makedirs(os.path.dirname(results_csv), exist_ok=True)
        file_exists = os.path.isfile(results_csv)
        
        header = [
            "serial_no", "measurement_id", "probe_id", "dst_addr", "from",
            "timestamp_unix", "timestamp_iso", "sent", "rcvd", "loss_pct",
            "min_ms", "avg_ms", "max_ms", "rtt1", "rtt2", "rtt3"
        ]
        
        with open(results_csv, "a" if file_exists else "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow(header)
            
            for idx, result in enumerate(results, start=1):
                row = [
                    idx,
                    result.measurement_id,
                    result.probe_id,
                    result.target,
                    result.source_address,
                    result.timestamp,
                    result.timestamp_iso,
                    result.sent,
                    result.received,
                    result.loss_percentage,
                    result.min_rtt,
                    result.avg_rtt,
                    result.max_rtt,
                    result.rtt1,
                    result.rtt2,
                    result.rtt3,
                ]
                writer.writerow(row)