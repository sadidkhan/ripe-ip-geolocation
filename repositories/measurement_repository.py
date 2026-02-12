"""Measurement repository for data persistence."""
import csv
import os
from pathlib import Path
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, text
from models import Measurement
from models.measurement import PingResult


class MeasurementRepository:
    """Handles measurement data persistence to database and CSV."""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize repository with optional database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
     
    
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
    
    def read_fetched_results(self, results_csv: Path) -> list[int]:
        """Read measurement IDs that have already been fetched."""
        if not os.path.isfile(results_csv):
            return []
        
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
        return sorted(measurement_ids)
    
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
    
    # ============================================
    # DATABASE OPERATIONS
    # ============================================
    
    async def get_measurements_for_target_analysis(self):
        result = await self.session.execute(text("""
            With filter_records_by_rcvdPackets AS (
                SELECT DISTINCT
                    m.*,
                    i.asn,
                    i.as_name,
                    afp.probe_id as afp_probe_id,
                    afp.country_code
                FROM measurements AS m
                JOIN ip_info AS i
                    ON m.dst_addr = i.ip_address
                JOIN african_probes AS afp ON afp.probe_id = m.probe_id
                WHERE rcvd > 0
                --Select * from tmp_measurements_with_asn where rcvd > 0
            )
            SELECT 
                dst_addr,
                COUNT(*)                                  AS n_samples,
                MIN(m.avg_ms)                             AS min_rtt_ms,
                MAX(m.avg_ms)                             AS max_rtt_ms,
                AVG(m.avg_ms)                             AS mean_rtt_ms,
                STDDEV(m.avg_ms)                      AS stddev_rtt_ms,
                percentile_cont(0.05) WITHIN GROUP (ORDER BY m.avg_ms) AS p5_rtt_ms,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY m.avg_ms) AS p50_rtt_ms,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY m.avg_ms) AS p75_rtt_ms,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY m.avg_ms) AS p95_rtt_ms,

            -- spread metrics
            (percentile_cont(0.95) WITHIN GROUP (ORDER BY m.avg_ms)
            - percentile_cont(0.05) WITHIN GROUP (ORDER BY m.avg_ms)) AS ipr_95_5_ms
            
            FROM filter_records_by_rcvdPackets m
            GROUP BY dst_addr
        """))
        a = result.mappings().all()
        return a
    
    async def create_measurement(self, measurement: Measurement) -> dict:
        """Create a measurement in the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = insert(Measurement).values(
                id=measurement.id,
                target=measurement.target,
                measurement_type=measurement.measurement_type,
                status=measurement.status,
                created_at=measurement.created_at,
            )
            await self.session.execute(query)
            await self.session.commit()
            return {"status": "success", "measurement_id": measurement.id}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": str(e)}
    
    async def get_measurement(self, measurement_id: int) -> Optional[Measurement]:
        """Get a measurement from the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = select(Measurement).where(Measurement.id == measurement_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error fetching measurement: {e}")
            return None
    
    async def get_all_measurements(self) -> List[Measurement]:
        """Get all measurements from the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = select(Measurement)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error fetching measurements: {e}")
            return []
    
    async def update_measurement_status(self, measurement_id: int, status: str) -> dict:
        """Update measurement status in the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = update(Measurement).where(
                Measurement.id == measurement_id
            ).values(status=status)
            await self.session.execute(query)
            await self.session.commit()
            return {"status": "success", "measurement_id": measurement_id}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": str(e)}
    
    async def delete_measurement(self, measurement_id: int) -> dict:
        """Delete a measurement from the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = delete(Measurement).where(Measurement.id == measurement_id)
            await self.session.execute(query)
            await self.session.commit()
            return {"status": "success", "measurement_id": measurement_id}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": str(e)}