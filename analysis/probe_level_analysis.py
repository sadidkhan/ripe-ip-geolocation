try:
    from analysis.db_connection import get_db_connection
except ModuleNotFoundError:
    from db_connection import get_db_connection
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

def get_sql_probe_for_country_p50_p95():
    return """
            With filter_records_by_rcvdPackets AS (
                SELECT DISTINCT
                    m.*,
                    i.asn,
                    i.as_name,
                    afp.probe_id as afp_probe_id,
                    afp.country_code
                FROM measurements AS m
                JOIN ip_info AS i
                    ON m.dst_addr = i.ip_address
                JOIN african_probes AS afp ON afp.probe_id = m.probe_id
                WHERE rcvd > 0
                --Select * from tmp_measurements_with_asn where rcvd > 0
            )
            SELECT
                    probe_id,
                    country_code,
                    COUNT(*)                                  AS number_of_targets,
                    MIN(m.avg_ms)                             AS min_rtt_ms,
                    MAX(m.avg_ms)                             AS max_rtt_ms,
                    AVG(m.avg_ms)                             AS mean_rtt_ms,
                    STDDEV_SAMP(m.avg_ms)                      AS stddev_rtt_ms,
                    percentile_cont(0.05) WITHIN GROUP (ORDER BY m.avg_ms) AS p5_rtt_ms,
                    percentile_cont(0.50) WITHIN GROUP (ORDER BY m.avg_ms) AS p50_rtt_ms,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY m.avg_ms) AS p75_rtt_ms,
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY m.avg_ms) AS p95_rtt_ms,
                
                -- spread metrics
                (percentile_cont(0.95) WITHIN GROUP (ORDER BY m.avg_ms)
                - percentile_cont(0.05) WITHIN GROUP (ORDER BY m.avg_ms)) AS ipr_95_5_ms,
                    
                    AVG(CASE WHEN m.avg_ms <= 50 THEN 1.0 ELSE 0.0 END) AS frac_targets_le_50ms

            FROM filter_records_by_rcvdPackets m
            GROUP BY probe_id, country_code
            ORDER BY frac_targets_le_50ms
        """

def plot_country_p95_boxplot():
    
    with get_db_connection() as conn:
        # 1) Load
        df = pd.read_sql(get_sql_probe_for_country_p50_p95(), conn)
        
    df = df[["country_code", "p95_rtt_ms"]].dropna()

    # Sort countries by median p95
    country_order = (
        df.groupby("country_code")["p95_rtt_ms"]
        .median()
        .sort_values(ascending=False)
        .index
        .tolist()
    )

    data = [df[df["country_code"] == c]["p95_rtt_ms"].values for c in country_order]

    plt.figure(figsize=(10, max(6, len(country_order) * 0.28)))
    plt.boxplot(data, vert=False, showfliers=False)

    plt.yticks(range(len(country_order)), country_order)
    plt.xlabel("RTT (ms)")
    plt.title("Country-level Probe Tail RTT (p95)")

    plt.tight_layout()
    plt.show()
        
    
def plot_country_p50_boxplot():
    with get_db_connection() as conn:
        df = pd.read_sql(get_sql_probe_for_country_p50_p95(), conn)
        
    df = df[["country_code", "p50_rtt_ms"]].dropna()

    # Sort countries by median p50
    country_order = (
        df.groupby("country_code")["p50_rtt_ms"]
          .median()
          .sort_values(ascending=False)
          .index
          .tolist()
    )

    data = [df[df["country_code"] == c]["p50_rtt_ms"].values for c in country_order]

    plt.figure(figsize=(10, max(6, len(country_order) * 0.28)))
    plt.boxplot(data, vert=False, showfliers=False)

    plt.yticks(range(len(country_order)), country_order)
    plt.xlabel("RTT (ms)")
    plt.title("Country-level Probe Median RTT (p50)")

    plt.tight_layout()
    plt.show()    
