WITH per_ip AS (
    SELECT
        m.dst_addr,
        i.asn,
        i.as_name,
        COUNT(*) AS total_probes,
        100.0 * COUNT(*) FILTER (WHERE m.avg_ms <= 50) / COUNT(*) AS pct_le_50ms
    FROM measurements AS m
    JOIN ip_info AS i
        ON m.dst_addr = i.ip_address
    GROUP BY
        m.dst_addr,
        i.asn,
        i.as_name
)
SELECT
    asn,
    as_name,
    COUNT(*) AS num_dst_addrs,
    ROUND(MIN(pct_le_50ms), 2) AS min_pct_le_50ms,
    ROUND(MAX(pct_le_50ms), 2) AS max_pct_le_50ms,
    ROUND(
        (percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_le_50ms))::numeric,
        2
    ) AS median_pct_le_50ms
FROM per_ip
GROUP BY
    asn,
    as_name
ORDER BY
    asn;
