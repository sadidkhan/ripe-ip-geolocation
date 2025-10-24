from datetime import datetime
import os
import csv
import time


def read_probes_from_csv(csv_path):
    probes = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                probes.append(dict(row))
    except FileNotFoundError:
        pass
    return probes


def write_probes_to_csv(self, probes, csv_path):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if probes:
        keys = sorted(probes[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(probes)


def read_measurements(file_path):
    measurements = {}
    with open(file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            target = row.get('target')
            measurement_id = row.get('measurement_id')
            if target and measurement_id:  # ensure both are not empty
                measurements[target.strip()] = measurement_id.strip()
    return measurements


def write_single_msm_id(target: str, msm_id: int, path: str = "data/measurements/measurements.csv"):
        if msm_id is None:
            return
        
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        new_file = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["target", "measurement_id"])
            w.writerow([target, msm_id])
            

def write_failed_msm_target(target: str, error: str, path: str = "data/measurements/failed.csv"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    new_file = not os.path.exists(path)
    # Keep error line sane
    error = (error or "").strip().replace("\n", " ")[:500]
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["target", "timestamp", "error"])
        w.writerow([target, datetime.now().isoformat(timespec="seconds"), error])


def read_fetched_ping_msm_result(csv_path: str) -> set[int]:
    """
    Read measurement IDs from an existing CSV and return them as a set.
    Useful for quickly checking if a measurement_id is already processed.
    """
    if not os.path.isfile(csv_path):
        return set()

    measurement_ids = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            msm_id = row.get("measurement_id")
            if msm_id:  # skip empty lines
                try:
                    measurement_ids.add(int(msm_id))
                except ValueError:
                    continue  # skip malformed values
    return measurement_ids


def save_fetched_ping_msm_result(data, out_csv="data/measurements/ping_result_fixed3.csv"):
        if not data:
            return
        
        # Define header once
        header = [
            "serial_no",
            "measurement_id", "probe_id", "dst_addr", "from",
            "timestamp_unix", "timestamp_iso",
            "sent", "rcvd", "loss_pct",
            "min_ms", "avg_ms", "max_ms",
            "rtt1", "rtt2", "rtt3"
        ]

        # Check if file exists
        file_exists = os.path.isfile(out_csv)

        # Open in append or write mode accordingly
        with open(out_csv, "a" if file_exists else "w", newline="") as f:
            writer = csv.writer(f)
            # Write header if file is new
            if not file_exists:
                writer.writerow(header)

            # Each element in data = one probe’s ping result
            counter = 0
            for pr in data:
                counter += 1
                rtts = [pkt.get("rtt") for pkt in pr.get("result", []) if pkt.get("rtt") is not None]
                rtts += [None] * (3 - len(rtts))  # pad to 3 RTTs if fewer

                sent = pr.get("sent", 0)
                rcvd = pr.get("rcvd", 0)
                loss_pct = round(100.0 * (max(sent - rcvd, 0)) / sent, 2) if sent else 0.0

                ts = pr.get("timestamp")
                ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)) if ts else ""

                row = [
                    counter,
                    pr.get("msm_id") or pr.get("group_id"),
                    pr.get("prb_id"),
                    pr.get("dst_addr") or pr.get("dst_name"),
                    pr.get("from") or pr.get("src_addr"),
                    ts, ts_iso,
                    sent, rcvd, loss_pct,
                    pr.get("min"), pr.get("avg"), pr.get("max"),
                    rtts[0], rtts[1], rtts[2],
                ]

                writer.writerow(row)