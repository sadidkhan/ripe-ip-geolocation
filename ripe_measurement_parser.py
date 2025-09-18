import json

class RipeMeasurementParser:
    def __init__(self, json_file):
        self.json_file = json_file

    def parse_measurements(self):
        measurements = []
        with open(self.json_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                measurement = json.loads(line)
                src = measurement.get("src_addr")
                dst = measurement.get("dst_addr")
                destination_ip_responded = measurement.get("destination_ip_responded")
                prb_id = measurement.get("prb_id")

                traceroute = []
                for hop in measurement.get("result", []):
                    hop_num = hop.get("hop")
                    hop_result = hop.get("result", [])
                    if hop_result and "from" in hop_result[0]:
                        from_addr = hop_result[0].get("from")
                        rtt = hop_result[0].get("rtt")
                        traceroute.append({"hop": hop_num, "from": from_addr, "rtt": rtt})
                    elif hop_result and "x" in hop_result[0]:
                        traceroute.append({"hop": hop_num, "from": "*", "rtt": None})

                measurements.append({
                    "src_addr": src,
                    "dst_addr": dst,
                    "destination_ip_responded": destination_ip_responded,
                    "prb_id": prb_id,
                    "traceroute": traceroute
                })
        return measurements