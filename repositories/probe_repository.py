"""Probe repository for data persistence."""
import csv
import os
from pathlib import Path
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, text
from models.probe import Probe


class ProbeRepository:
    """Handles probe data persistence to CSV and Database."""
    
    def __init__(self, csv_path: Optional[Path] = None, session: Optional[AsyncSession] = None):
        """
        Initialize repository with optional CSV path and database session.
        
        Args:
            csv_path: Path to CSV file for CSV operations
            session: AsyncSession for database operations
        """
        self.csv_path = csv_path
        self.session = session
        
    def read_probes_from_csv(self):
        if not os.path.exists(self.csv_path):
            return []
        
        probes = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                probes.append(dict(row))
        return probes
    
    def write_probes_to_csv(self, probes):
        if not probes:
            return
        
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        keys = sorted(probes[0].keys())
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(probes)
    
    
    # def read_all(self) -> list[Probe]:
    #     """Read all probes from CSV."""
    #     if not os.path.exists(self.csv_path):
    #         return []
        
    #     probes = []
    #     with open(self.csv_path, "r", encoding="utf-8") as f:
    #         reader = csv.DictReader(f)
    #         for row in reader:
    #             # Convert string values to appropriate types
    #             probe_dict = {
    #                 "id": int(row.get("id", 0)),
    #                 "country_code": row.get("country_code", ""),
    #                 "asn_v4": int(row["asn_v4"]) if row.get("asn_v4") else None,
    #                 "asn_v6": int(row["asn_v6"]) if row.get("asn_v6") else None,
    #                 "status": int(row["status"]) if row.get("status") else None,
    #                 "latitude": float(row["latitude"]) if row.get("latitude") else None,
    #                 "longitude": float(row["longitude"]) if row.get("longitude") else None,
    #                 "address_v4": row.get("address_v4"),
    #                 "address_v6": row.get("address_v6"),
    #                 "prefix_v4": row.get("prefix_v4"),
    #                 "prefix_v6": row.get("prefix_v6"),
    #                 "is_anchor": row.get("is_anchor", "").lower() == "true",
    #                 "is_public": row.get("is_public", "").lower() == "true",
    #             }
    #             probes.append(Probe(**probe_dict))
    #     return probes
    
    # def write_all(self, probes: list[Probe]) -> None:
    #     """Write all probes to CSV."""
    #     if not probes:
    #         return
        
    #     os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        
    #     with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
    #         fieldnames = [
    #             "id", "country_code", "asn_v4", "asn_v6", "status",
    #             "latitude", "longitude", "address_v4", "address_v6",
    #             "prefix_v4", "prefix_v6", "is_anchor", "is_public"
    #         ]
    #         writer = csv.DictWriter(f, fieldnames=fieldnames)
    #         writer.writeheader()
    #         writer.writerows([probe.to_dict() for probe in probes])
    
    def exists(self) -> bool:
        """Check if probe data file exists."""
        return os.path.exists(self.csv_path) and os.path.getsize(self.csv_path) > 0
    
    # ============================================
    # DATABASE OPERATIONS
    # ============================================
    
    async def create_probe(self, probe: Probe) -> dict:
        """Create a probe in the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = insert(Probe).values(
                id=probe.id,
                country_code=probe.country_code,
                asn_v4=probe.asn_v4,
                asn_v6=probe.asn_v6,
                status=probe.status,
                latitude=probe.latitude,
                longitude=probe.longitude,
                address_v4=probe.address_v4,
                address_v6=probe.address_v6,
                prefix_v4=probe.prefix_v4,
                prefix_v6=probe.prefix_v6,
                is_anchor=probe.is_anchor,
                is_public=probe.is_public,
            )
            await self.session.execute(query)
            await self.session.commit()
            return {"status": "success", "probe_id": probe.id}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": str(e)}
    
    async def get_probe(self, probe_id: int) -> Optional[Probe]:
        """Get a probe from the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = select(Probe).where(Probe.id == probe_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"Error fetching probe: {e}")
            return None
    
    async def get_all_probes(self) -> List[Probe]:
        """Get all probes from the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = select(Probe)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error fetching probes: {e}")
            return []
    
    async def get_probes_by_country(self, country_code: str) -> List[Probe]:
        """Get all probes for a specific country."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = select(Probe).where(Probe.country_code == country_code)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            print(f"Error fetching probes for {country_code}: {e}")
            return []
    
    async def delete_probe(self, probe_id: int) -> dict:
        """Delete a probe from the database."""
        if not self.session:
            raise RuntimeError("Database session not initialized")
        
        try:
            query = delete(Probe).where(Probe.id == probe_id)
            await self.session.execute(query)
            await self.session.commit()
            return {"status": "success", "probe_id": probe_id}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": str(e)}