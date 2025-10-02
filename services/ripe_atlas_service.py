from ripe_atlas_client import RipeAtlasClient


class RipeAtlasService:
    def __init__(self):
        self.client = RipeAtlasClient()
        self.__probes = []


    async def get_probes_from_Africa(self):
        probes = await self.get_probes()
        return self.filter_african_probes()


    async def get_probes(self):
        async with self.client as client:
            async for probe in client.get_probes():
                self.__probes.append(probe)
            return {"probes": self.probes}
    

    def filter_african_probes(self):
        african_countries = {
            "DZ", "AO", "BJ", "BW", "BF", "BI", "CM", "CV", "CF", "TD", "KM",
            "CD", "CG", "CI", "DJ", "EG", "GQ", "ER", "SZ", "ET", "GA", "GM",
            "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG", "MW", "ML", "MR",
            "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN", "SC", "SL",
            "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "ZM", "ZW"
        }
        return [probe for probe in self.__probes if probe.get("country_code") in african_countries]
    
    def filter_probes_by_country(self, country_code):
        return [probe for probe in self.__probes if probe.get("country_code") == country_code]

    async def close(self):
        await self.client.aclose()
