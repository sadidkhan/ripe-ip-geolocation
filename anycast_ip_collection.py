import pandas as pd
import os
import csv

import logging

from geo_lite_client import GeoLiteClient
from ip_info_client import IpinfoClient
logger = logging.getLogger("ripe_atlas")

def get_anycast_list(date_str: str = "2025/10/08", param_value: int = 0):
    """
    Fetch and filter anycast IPs from anycast-census CSV for a given date.

    Args:
        date_str (str): Date in format 'YYYY/MM/DD', e.g. '2025/10/08'
        param_value (int): Minimum number_of_sites threshold.
    """
    base_url = "https://raw.githubusercontent.com/ut-dacs/anycast-census/main/"
    csv_url = f"{base_url}{date_str}/IPv4.csv"

    # Load and process data
    df = pd.read_csv(csv_url)
    filtered = df[df["number_of_sites"] > param_value].sort_values(
        by="number_of_sites", ascending=False
    )
    return filtered


def build_anycast_dict(df):
    """
    Given a DataFrame of anycast prefixes (with 'prefix' column),
    return a dictionary where:
        key   = first three octets (e.g., '1.0.0')
        value = prefix string (e.g., '1.0.0.0/24')
    """
    anycast_dict = {}

    for _,row in df.iterrows():
        prefix = row["prefix"]
        num_sites = row["number_of_sites"]
        try:
            base = ".".join(prefix.split(".")[:3])
            anycast_dict[base] = {"prefix": prefix, "num_sites": num_sites}
        except Exception as e:
            logger.error(f"Error processing row {row}: {e}")
            continue
        
    return anycast_dict


# fsdb_reader.py
def retrieve_ips_from_fsdb_hitlist(anycast_dict, fsdb_path: str = "data/anycast/internet_address_hitlist_it113w-20250827.fsdb"):
    """
    Reads an FSDB file and returns a list of rows (as lists)
    where the 'score' value is > 0.
    """
    # anycast_df = get_anycast_list(date_str="2025/10/08", param_value=0)
    # anycast_dict = build_anycast_dict(anycast_df)

    result = []
    with open(fsdb_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # skip comments or empty lines

            parts = line.split()
            try:
                score = int(parts[1])
                if score > 0:
                    ip = parts[2]
                    base = ".".join(ip.split(".")[:3])
                    if base in anycast_dict:
                        anycast_dict[base]["ip"] = ip
                        result.append(ip)
            except ValueError:
                print(f"this line has a non-integer score: {line}")
                continue  # skip malformed lines

    return result

def get_final_anycast_ips(anycast_dict):
    ips = []
    for key, val in anycast_dict.items():
        if "ip" in val:
            ips.append(val["ip"])
    return ips

def write_ip_list_to_csv(ip_list, filename, columns=["ip"]):
    """
    Write a list of IPs to a CSV file with a single column 'ip'.
    """
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        for ip in ip_list:
            writer.writerow([ip])

def get_anycast_ips():
    csv_path = "data/anycast/anycast_ip_list.csv"
    if os.path.exists(csv_path):
        ips = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ips.append(row["ip"])
        return ips
    else:
        anycast_df = get_anycast_list(date_str="2025/10/08", param_value=0)
        anycast_dict = build_anycast_dict(anycast_df)
        matched_ips = retrieve_ips_from_fsdb_hitlist(anycast_dict)
        ips = get_final_anycast_ips(anycast_dict)
        write_ip_list_to_csv(ips, csv_path)
        return matched_ips
    


async def get_anycast_ip_details():
   
    OUTPUT_FILE = "data/anycast/anycast_ip_details.csv"
    BATCH_SIZE = 10
    FIELDNAMES = [
        "ip_address", "asn", "as_name", "as_domain", "as_org",
        "country_code", "country",
        "continent", "continent_code"
    ]

    # ensure dir & figure out header need
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    header_needed = not (os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0)

    ips = get_anycast_ips()

    # read existing IPs (if any) to avoid duplicate lookups/writes
    existing_ips = set()
    if not header_needed:
        with open(OUTPUT_FILE, "r", newline="", encoding="utf-8") as rf:
            reader = csv.DictReader(rf)
            for row in reader:
                ip = row.get("ip_address")
                if ip:
                    existing_ips.add(ip)

    new_ips = [ip for ip in ips if ip not in existing_ips]
    skipped_existing = len(ips) - len(new_ips)
    if not new_ips:
        logger.info("Nothing to do: all %d IPs already recorded.", len(ips))
        return {"seen": len(ips), "skipped_existing": skipped_existing, "written": 0, "errors": 0}

    written = 0
    errors = 0

    async with IpinfoClient() as ipinfo, GeoLiteClient() as geolite:
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as wf:
            writer = csv.DictWriter(wf, fieldnames=FIELDNAMES)
            if header_needed:
                writer.writeheader()

            # process in batches
            for batch_start in range(0, len(new_ips), BATCH_SIZE):
                batch = new_ips[batch_start: batch_start + BATCH_SIZE]
                logger.info("Processing batch %d (%d IPs)", batch_start // BATCH_SIZE + 1, len(batch))

                for ip in batch:
                    try:
                        ipinfo_data = await ipinfo.lookup(ip)
                        #geolite_data = await geolite.city(ip)

                        if not ipinfo_data: #or not geolite_data:
                            logger.warning("Skipping %s: missing data", ip)
                            errors += 1
                            continue

                        row = {
                            "ip_address": ip,
                            "asn": ipinfo_data.get("asn"),
                            #"as_num": geolite_data.as_num,
                            "as_name": ipinfo_data.get("as_name"),
                            "as_domain": ipinfo_data.get("as_domain"),
                            #"as_org": geolite_data.as_org,
                            "country_code": ipinfo_data.get("country_code"),
                            "country": ipinfo_data.get("country"),
                            #"registered_country": getattr(geolite_data, "registered_country", None),
                            #"registered_country_iso": getattr(geolite_data, "registered_country_iso", None),
                            "continent": ipinfo_data.get("continent"),
                            "continent_code": ipinfo_data.get("continent_code"),
                            # "latitude": getattr(geolite_data, "latitude", None),
                            # "longitude": getattr(geolite_data, "longitude", None),
                            # "accuracy_radius_km": getattr(geolite_data, "accuracy_radius_km", None),
                            # "network": geolite_data.network,
                            # "time_zone": getattr(geolite_data, "time_zone", None),
                        }

                        try:
                            writer.writerow(row)
                            written += 1
                        except Exception as write_err:
                            errors += 1
                            logger.exception("Write error for %s: %s", ip, write_err)

                    except Exception as fetch_err:
                        errors += 1
                        logger.exception("Lookup error for %s: %s", ip, fetch_err)

                # persist once per batch
                try:
                    wf.flush()
                    os.fsync(wf.fileno())
                except Exception as fs_err:
                    logger.warning("Flush/fsync warning: %s", fs_err)

    logger.info("Done. Seen=%d, Skipped(existing)=%d, Written=%d, Errors=%d",
                len(ips), skipped_existing, written, errors)
    return {"seen": len(ips), "skipped_existing": skipped_existing, "written": written, "errors": errors}

