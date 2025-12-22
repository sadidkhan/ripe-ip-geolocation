import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import matplotlib.pyplot as plt
import os
from contextlib import contextmanager



# TODO: fill these from your local setup
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

@contextmanager
def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()



def plot_Latency():
    with get_db() as conn:
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
    conn = psycopg2.connect(**DB_CONFIG)
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


def main():
    plot_Latency()

if __name__ == "__main__":
    main()