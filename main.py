import asyncio
from geo_lite_client import GeoLiteClient
from ip_info_client import IpinfoClient


async def main():
    async with IpinfoClient() as ipinfo, \
               GeoLiteClient() as geolite:

        ip = "8.8.8.8"

        ipinfo_data = await ipinfo.lookup(ip)
        print("ipinfo:", ipinfo_data)

        geolite_data = await geolite.city(ip)
        print("geolite:", geolite_data)


if __name__ == "__main__":
    asyncio.run(main())