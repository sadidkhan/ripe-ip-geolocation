from ripe_atlas_client import RipeAtlasClient

AFRICAN_COUNTRIES: frozenset[str] = frozenset({
    "DZ","AO","BJ","BW","BF","BI","CM","CV","CF","TD","KM",
    "CD","CG","CI","DJ","EG","GQ","ER","SZ","ET","GA","GM",
    "GH","GN","GW","KE","LS","LR","LY","MG","MW","ML","MR",
    "MU","MA","MZ","NA","NE","NG","RW","ST","SN","SC","SL",
    "SO","ZA","SS","SD","TZ","TG","TN","UG","ZM","ZW"
})

class RipeAtlasService:

    def __init__(self):
        self.client = RipeAtlasClient()
        self.__probes = []


    async def fetch_all_probes(self):
        probes = []
        async with RipeAtlasClient() as client:
            async for probe in client.get_probes():
                probes.append(probe)
        return probes
    

    def filter_african_probes(self):
        return [probe for probe in self.__probes if probe.get("country_code") in AFRICAN_COUNTRIES]
    
    
    async def get_probes_from_Africa(self):
        if not self.__probes:
            self.__probes = await self.fetch_all_probes()
        return self.filter_african_probes()
    
    
    async def create_measurement(self):
            #ids = [probe["id"] for probe in self.__probes[:2]]  # Example: first 2 probes
            #value_str = ",".join(map(str, ids))
            value_str = "242"

            # if not ids:
            #     raise ValueError("No probes available to create a measurement.")
            

            measurement_data = {
                "definitions": [
                    {
                        "target": "1.1.1.1",
                        "description": "test first measurement",
                        "type": "traceroute",
                        "af": "4",
                        "is_oneoff": True
                    }
                ],
                "probes": [
                    {
                        "requested": 1, #len(ids),
                        "type": "probes",
                        "value": value_str,
                        # # modern tag filters:
                        # "tags_include": TAGS_INCLUDE,
                        # "tags_exclude": TAGS_EXCLUDE
                    }
                ],
            }
            async with self.client as client:
                return await client.create_measurement(measurement_data)

    async def close(self):
        await self.client.aclose()
