import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

try:
    from analysis.probe_level_analysis import plot_country_p95_boxplot, plot_country_p50_boxplot
    from analysis.db_connection import get_db_connection, get_db_config
except ModuleNotFoundError:
    from probe_level_analysis import plot_country_p95_boxplot, plot_country_p50_boxplot
    from db_connection import get_db_connection, get_db_config



def plot_Latency():
    with get_db_connection() as conn:
        df = pd.read_sql("""SELECT
                dst_addr,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE avg_ms <= 50)         AS lt_50ms,
                COUNT(*) FILTER (WHERE avg_ms > 50)          AS gt_50ms,
                ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms <= 50) / COUNT(*), 2) AS pct_lt_50ms,
                ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms > 50) / COUNT(*), 2) AS pct_gt_50ms
            FROM measurements
            GROUP BY dst_addr
            ORDER BY pct_lt_50ms;""", conn)
        
        result = df
        # CDF over pct_lt_50ms across targets
        df_sorted = df.sort_values("pct_lt_50ms").reset_index(drop=True)
        n = len(df_sorted)
        df_sorted["fraction_of_targets"] = (df_sorted.index + 1) / n  # y-axis

        # x: pct of fast probes per target, y: fraction of targets
        plt.plot(df_sorted["pct_lt_50ms"], df_sorted["fraction_of_targets"])
        plt.xlabel("Percent of probes with ≤ 50 ms (per target)")
        plt.ylabel("Fraction of targets")
        plt.title("CDF of percentage of probes with ≤ 50 ms across targets")
        plt.grid(True)
        plt.show()
        input("Press Enter to exit...")

        


def plot_cdf():
    conn = psycopg2.connect(**get_db_config())
    try:
        # Pull raw latency data
        df = pd.read_sql(
            """SELECT
                dst_addr,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE avg_ms <= 50)         AS lt_50ms,
                COUNT(*) FILTER (WHERE avg_ms > 50)          AS gt_50ms,
                ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms <= 50) / COUNT(*), 2) AS pct_lt_50ms,
                ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms > 50) / COUNT(*), 2) AS pct_gt_50ms
            FROM measurements
            GROUP BY dst_addr
            ORDER BY dst_addr;""",
            conn
        )

    finally:
        conn.close()

    # Plot CDF per dst_addr
    for dst_addr, group in df.groupby("dst_addr"):
        sorted_vals = group["avg_ms"].sort_values()
        cdf = sorted_vals.rank(method="first") / len(sorted_vals)
        plt.plot(sorted_vals, cdf, label=str(dst_addr))

    plt.xlabel("Latency (ms)")
    plt.ylabel("CDF")
    plt.title("Latency CDF per target")
    plt.legend()
    plt.grid(True)
    plt.show()
    

def cdf():
    
    with get_db_connection() as conn:
        df = pd.read_sql("""
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
                dst_addr,
                COUNT(*)                                  AS n_samples,
                MIN(m.avg_ms)                             AS min_rtt_ms,
                MAX(m.avg_ms)                             AS max_rtt_ms,
                AVG(m.avg_ms)                             AS mean_rtt_ms,
                STDDEV(m.avg_ms)                      AS stddev_rtt_ms,
                percentile_cont(0.05) WITHIN GROUP (ORDER BY m.avg_ms) AS p5_rtt_ms,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY m.avg_ms) AS p50_rtt_ms,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY m.avg_ms) AS p75_rtt_ms,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY m.avg_ms) AS p95_rtt_ms,

            -- spread metrics
            (percentile_cont(0.95) WITHIN GROUP (ORDER BY m.avg_ms)
            - percentile_cont(0.05) WITHIN GROUP (ORDER BY m.avg_ms)) AS ipr_95_5_ms
            
            FROM filter_records_by_rcvdPackets m
            GROUP BY dst_addr
        """, conn)

    # ---- Function to compute CDF ----
    def compute_cdf(series):
        sorted_vals = np.sort(series.values)
        cdf = np.arange(1, len(sorted_vals)+1) / len(sorted_vals)
        return sorted_vals, cdf

    # ---- Compute CDFs ----
    p5_vals, p5_cdf = compute_cdf(df["p5_rtt_ms"])
    p50_vals, p50_cdf = compute_cdf(df["p50_rtt_ms"])
    p95_vals, p95_cdf = compute_cdf(df["p95_rtt_ms"])

    # ---- Plot ----
    plt.figure(figsize=(12,6))

    plt.plot(p5_vals, p5_cdf, label="p5 (Best Case)")
    plt.plot(p50_vals, p50_cdf, label="p50 (Median)")
    plt.plot(p95_vals, p95_cdf, label="p95 (Worst Case)")

    plt.xlabel("Latency (ms)")
    plt.ylabel("Fraction of Prefixes (CDF)")
    plt.title("CDF of Prefix-Level Latency Percentiles")

    plt.legend()
    plt.grid(True)

    # Recommended for networking latency
    #plt.xscale("log")

    plt.tight_layout()
    plt.show()
    input("Press Enter to exit...")


def plot_prob_info():
    with get_db_connection() as conn:
        df = pd.read_sql("""
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
            select
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

            from filter_records_by_rcvdPackets m
            group by probe_id, country_code
            order by country_code
        """, conn)

    # Example 1: Top 20 worst probes by p95 across targets
    top = df.sort_values("p95_rtt_ms", ascending=False).head(20)

    plt.figure()
    plt.bar(top["dst_addr"].astype(str), top["p95_rtt_ms"])
    plt.xticks(rotation=90)
    plt.ylabel("p95 RTT across targets (ms)")
    plt.title("Top 20 worst probes (by p95 across targets)")
    plt.tight_layout()
    plt.show()

    # Example 2: Scatter: p50 vs p95 (stability)
    plt.figure()
    plt.scatter(df["p50_rtt_ms"], df["p95_rtt_ms"])
    plt.xlabel("p50 RTT across targets (ms)")
    plt.ylabel("p95 RTT across targets (ms)")
    plt.title("Probe stability: p50 vs p95 across targets")
    plt.tight_layout()
    plt.show()

    # Example 3: Fraction of targets <= 50ms
    plt.figure()
    plt.hist(df["frac_targets_le_50ms"], bins=20)
    plt.xlabel("Fraction of targets with RTT <= 50ms")
    plt.ylabel("Number of probes")
    plt.title("How many probes are 'mostly fast'?")
    plt.tight_layout()
    plt.show()



    


def main():
    # Map input strings to actual function objects
    menu_options = {
        "1": cdf,
        "2": plot_prob_info,
        "3": plot_country_p95_boxplot,
        "4": plot_country_p50_boxplot,
    }
    while True:
        print("\n--- Main Menu ---")
        print("1: Run CDF")
        print("2: Run Probe Info Plots")
        print("3: Plot Country p95 Boxplot")
        print("4: Plot Country p50 Boxplot")
        print("Type 'quit' or 'q' to exit")
        
        # Get user input and clean it up (lowercase and no spaces)
        choice = input("\nSelect an option: ").strip().lower()

        if choice in ['quit', 'q', 'exit']:
            print("Goodbye!")
            break  # This exits the loop and the program
        
        if choice in menu_options:
            menu_options[choice]()
        else:
            print(f"'{choice}' is not a valid option. Please try again.")

if __name__ == "__main__":
    main()