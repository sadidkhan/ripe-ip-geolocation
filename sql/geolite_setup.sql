create table geoip2_network (
  network cidr not null,
  geoname_id int,
  registered_country_geoname_id int,
  represented_country_geoname_id int,
  is_anonymous_proxy bool,
  is_satellite_provider bool,
  postal_code text,
  latitude numeric,
  longitude numeric,
  accuracy_radius int,
  is_anycast bool
);

-- step 2: import data
\copy geoip2_network from 'GeoIP2-City-Blocks-IPv4.csv' with (format csv, header);

-- step 3: create index
create index on geoip2_network using gist (network inet_ops);


-- step 4: create location table
create table geoip2_location (
  geoname_id int not null,
  locale_code text not null,
  continent_code text,
  continent_name text,
  country_iso_code text,
  country_name text,
  subdivision_1_iso_code text,
  subdivision_1_name text,
  subdivision_2_iso_code text,
  subdivision_2_name text,
  city_name text,
  metro_code int,
  time_zone text,
  is_in_european_union bool not null,
  primary key (geoname_id, locale_code)
);

-- step 5: import location data
\copy geoip2_location from 'GeoIP2-City-Locations-en.csv' with (format csv, header);


-- step 6: anycast ip info details table
CREATE TABLE ip_info (
    id SERIAL PRIMARY KEY,
    ip_address INET NOT NULL,
    asn TEXT,
    as_name TEXT,
    as_domain TEXT,
    as_org TEXT,
    country_code CHAR(2),
    country TEXT,
    continent TEXT,
    continent_code CHAR(2)
);

-- For fast lookup by IP
CREATE INDEX idx_ip_info_ip ON ip_info USING gist (ip_address inet_ops);

-- For fast lookup by ASN
CREATE INDEX idx_ip_info_asn ON ip_info (asn);


-- step-7: create measurement table and related indexes
CREATE TABLE measurements (
    id                BIGSERIAL PRIMARY KEY,
    measurement_id    BIGINT,
    probe_id          INTEGER,
    dst_addr          INET,
    src_addr          INET,
    timestamp_unix    BIGINT,
    timestamp_iso     TIMESTAMPTZ,
    sent              INTEGER,
    rcvd              INTEGER,
    loss_pct          REAL,
    min_ms            REAL,
    avg_ms            REAL,
    max_ms            REAL,
    rtt1              REAL,
    rtt2              REAL,
    rtt3              REAL
);


CREATE INDEX idx_measurements_measurement_id
    ON measurements (measurement_id);

CREATE INDEX idx_measurements_probe_id
    ON measurements (probe_id);

CREATE INDEX idx_measurements_dst_addr
    ON measurements (dst_addr);


-- get
SELECT
    dst_addr,
	COUNT(*) AS total,
    COUNT(*) FILTER (WHERE avg_ms <= 50)         AS lt_50ms,
	COUNT(*) FILTER (WHERE avg_ms > 50)          AS gt_50ms,
    --COUNT(*) FILTER (WHERE avg_ms >= 50 AND avg_ms < 100) AS btw_50_100ms,
    --COUNT(*) FILTER (WHERE avg_ms >= 100)          AS gt_100ms,

    ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms <= 50) / COUNT(*), 2)
        AS pct_lt_50ms,

	ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms > 50) / COUNT(*), 2) 
        AS pct_gt_50ms

    --ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms >= 50 AND avg_ms < 100) / COUNT(*), 2) 
        --AS pct_50_100ms,

    --ROUND(100.0 * COUNT(*) FILTER (WHERE avg_ms >= 100) / COUNT(*), 2) 
        --AS pct_gt_100ms
		
FROM measurements
GROUP BY dst_addr
ORDER BY dst_addr;

