import pandas as pd
import os
import csv

import logging
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

def write_ip_list_to_csv(ip_list, filename):
    """
    Write a list of IPs to a CSV file with a single column 'ip'.
    """
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ip"])
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