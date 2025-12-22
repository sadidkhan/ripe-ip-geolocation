import asyncio
from anycast_ip_collection import get_anycast_ip_details
from geo_lite_client import GeoLiteClient
from ip_info_client import IpinfoClient
from ripe_measurement_parser import RipeMeasurementParser


async def main():
    print("inside main")
    #await get_anycast_ip_details()

    await test_geo_data()

    # ripe_parser = RipeMeasurementParser("data/RIPE-Atlas-measurement-128134459.json")
    # measurements = ripe_parser.parse_measurements()

    # async with IpinfoClient() as ipinfo, GeoLiteClient() as geolite:
    #     for measurement in measurements:
    #         for trace in measurement["traceroute"]:
    #             ip = trace["from"]
    #             if ip == "*" or ip is None:
    #                 trace["ipinfo"] = None
    #                 trace["geolite"] = None
    #                 continue
    #             ipinfo_data = await ipinfo.lookup(ip)
    #             geolite_data = await geolite.city(ip)
    #             trace["ipinfo"] = ipinfo_data
    #             trace["geolite"] = geolite_data

    #     # Example: print the first measurement with enriched traceroute
    #     if measurements:
    #         print(measurements[0])

async def test_geo_data():
    async with IpinfoClient() as ipinfo, GeoLiteClient() as geolite:
         while True:
            ip = input("Enter IP (or 'exit' to quit): ").strip()
            if ip.lower() == "exit":
                print("Exiting...")
                break

            try:
                geolite_data = await geolite.city(ip)
                ipinfo_data = await ipinfo.lookup(ip)

                print("\n=== RESULT ===")
                print("IP:", ip)
                print("GeoLite:", geolite_data)
                print("IPInfo:", ipinfo_data)
                print("==============\n")

            except Exception as e:
                print(f"Error processing {ip}: {e}")

    

if __name__ == "__main__":
    asyncio.run(main())