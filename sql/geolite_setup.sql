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

