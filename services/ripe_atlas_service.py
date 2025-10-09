from anycast_ip_collection import get_anycast_ips
from ripe_atlas_client import RipeAtlasClient
from typing import Literal
import os
import csv


AFRICAN_COUNTRIES: frozenset[str] = frozenset({
    "DZ","AO","BJ","BW","BF","BI","CM","CV","CF","TD","KM",
    "CD","CG","CI","DJ","EG","GQ","ER","SZ","ET","GA","GM",
    "GH","GN","GW","KE","LS","LR","LY","MG","MW","ML","MR",
    "MU","MA","MZ","NA","NE","NG","RW","ST","SN","SC","SL",
    "SO","ZA","SS","SD","TZ","TG","TN","UG","ZM","ZW"
})

class RipeAtlasService:

    @staticmethod
    def read_probes_from_csv(csv_path):
        """
        Read probes from a CSV file and return as a list of dictionaries.
        """
        import csv
        probes = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    probes.append(dict(row))
        except FileNotFoundError:
            pass
        return probes

    def __init__(self):
        self.client = RipeAtlasClient()


    async def fetch_all_probes(self):
        probes = []
        async with RipeAtlasClient() as client:
            async for probe in client.get_probes():
                probes.append(probe)
        return probes

    def write_probes_to_csv(self, probes, csv_path):
        import csv
        import os
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        if probes:
            keys = sorted(probes[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(probes)
    

    def filter_african_probes(self, probes):
        return [probe for probe in probes if probe.get("country_code") in AFRICAN_COUNTRIES]
    
    
    async def get_probes(self):
        probes = self.read_probes_from_csv("data/ripe/all_active_probes.csv")
        if not probes:
            probes = await self.fetch_all_probes()
            self.write_probes_to_csv(probes, "data/ripe/all_active_probes.csv")
        return probes
    
    
    def write_single_msm_id(self, target: str, msm_id: int, path: str = "data/measurements/measurements.csv"):
        if msm_id is None:
            return
        
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        new_file = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["target", "measurement_id"])
            w.writerow([target, msm_id])

    
    async def create_measurement(self, target, probes, type: Literal["ping", "traceroute"] = "ping"):
        if not probes:
            raise ValueError("No probes available to create a measurement.")

        ids = [probe["id"] for probe in probes[:2]]  # Example: first 2 probes
        value_str = ",".join(map(str, ids))

        measurement_data = {
            "definitions": [
                {
                    "target": target,
                    "description": f"{type} measurement for {target}",
                    "type": type,
                    "af": "4",
                    "is_oneoff": True  # it should be always true
                }
                ], 
                "probes": [
                    {
                        "requested": len(ids),
                        "type": "probes",
                        "value": value_str,
                        # # modern tag filters:
                        # "tags_include": TAGS_INCLUDE,
                        # "tags_exclude": TAGS_EXCLUDE
                    }
                ],
            }
            
        async with RipeAtlasClient() as client:
            response = await client.create_measurement(target, measurement_data)
            return response.get("measurements", [])
            
            
    
    async def initiate_measurement(self):
        targets = get_anycast_ips()
        probes = await self.get_probes()
        probes_from_africa = self.filter_african_probes(probes)
        for target in targets:
            try:
                measurements = await self.create_measurement(target, probes_from_africa, type="ping")
                msm_id = measurements[0] if measurements else None
                if msm_id:
                    self.write_single_msm_id(target, msm_id)

            except Exception as e:
                print(f"Error creating measurement for {target}: {e}")
            

    async def close(self):
        await self.client.aclose()
