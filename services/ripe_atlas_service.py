import asyncio
import time
from anycast_ip_collection import get_anycast_ips
from ripe_atlas_client import RipeAtlasClient
from typing import Literal
import os
import csv
from utility import read_fetched_ping_msm_result, read_measurements, save_fetched_ping_msm_result, write_failed_msm_target, write_single_msm_id

import logging
logger = logging.getLogger("ripe_atlas")


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
    
    async def get_african_probes(self):
        african_probes = self.read_probes_from_csv("data/ripe/african_active_probes.csv")
        if not african_probes:
            probes = await self.get_probes()
            african_probes = self.filter_african_probes(probes)
            self.write_probes_to_csv(african_probes, "data/ripe/african_active_probes.csv")
        return african_probes
    
    # def write_single_msm_id(self, target: str, msm_id: int, path: str = "data/measurements/measurements.csv"):
    #     if msm_id is None:
    #         return
        
    #     os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    #     new_file = not os.path.exists(path)
    #     with open(path, "a", newline="", encoding="utf-8") as f:
    #         w = csv.writer(f)
    #         if new_file:
    #             w.writerow(["target", "measurement_id"])
    #         w.writerow([target, msm_id])

    
    async def create_measurement(self, target, probes_str, num_of_probes, type: Literal["ping", "traceroute"] = "ping"):
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
                        "requested": num_of_probes,
                        "type": "probes",
                        "value": probes_str,
                        # # modern tag filters:
                        # "tags_include": TAGS_INCLUDE,
                        # "tags_exclude": TAGS_EXCLUDE
                    }
                ],
            }

        try:
            async with RipeAtlasClient() as client:
                response = await client.create_measurement(target, measurement_data)
                return response.get("measurements", [])
        except Exception as e:
            raise e

    async def initiate_measurement(self):
        targets = get_anycast_ips()
        #probes = await self.get_probes()
        probes_from_africa = await self.get_african_probes()

        if not probes_from_africa:
            raise ValueError("No african probes available to create a measurement.")
        
        ids = [probe["id"] for probe in probes_from_africa]  # Example: all probes
        probes_value_str = ",".join(map(str, ids))

        done_already = read_measurements("data/measurements/measurements.csv")
        counter = 0
        for target in targets:
            if target in done_already:
                continue
            try:
                counter += 1
                measurements = await self.create_measurement(target, probes_value_str, len(ids), type="ping")
                msm_id = measurements[0] if measurements else None
                if msm_id:
                    write_single_msm_id(target, msm_id)
                
                if(counter == 90):
                    await asyncio.sleep(300)  # Pause for 300 seconds (5 minutes)
                    counter = 0

            except Exception as e:
                write_failed_msm_target(target, str(e))
                print(f"Error creating measurement for {target}: {e}")
                # await asyncio.sleep(120)  # Pause before next attempt
    

    async def process_ping_msm_results(self):
        results = []
        async for data in self.get_msm_ping_results():
            if data:
                # results.append(data)
                save_fetched_ping_msm_result(data)

    
    async def get_msm_ping_results_batch(self, batch_size: int = 10):
        done_already = read_measurements("data/measurements/measurements.csv")
        msm_ids = list(done_already.values())

        results = []
        async with RipeAtlasClient() as client:
            for i in range(0, len(msm_ids), batch_size):
                batch = msm_ids[i:i + batch_size]

                tasks = [client.get_measurement(int(msm_id)) for msm_id in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Keep successes, log failures
                for msm_id, res in zip(batch, batch_results):
                    if isinstance(res, Exception):
                        print(f"⚠️ measurement {msm_id} failed: {res}")
                    else:
                        results.append(res)

                # Optional small pause to be nice to the API
                await asyncio.sleep(10)

        return results
    

    async def get_msm_ping_results(self):
        done_already = read_measurements("data/measurements/measurements.csv")
        msm_ids = list(done_already.values())
        already_fetched_msm = read_fetched_ping_msm_result("data/measurements/ping_result_fixed3.csv")

        counter = 0
        for msm_id in msm_ids:
            if int(msm_id) in already_fetched_msm:
                logger.info(f"Skipping already fetched measurement ID: {msm_id}")
                continue

            logger.info(f"Fetching results for measurement ID: {msm_id}")
            async with RipeAtlasClient() as client:
                response = await client.get_measurement_result(msm_id)
                yield response
            counter += 1
            if counter % 10 == 0:
                await asyncio.sleep(10)

    async def get_msm_ping_result_by_id(self, id):
        async with RipeAtlasClient() as client:
            response = await client.get_measurement(id)
            return response


    


    
        
        
            

    async def close(self):
        await self.client.aclose()
