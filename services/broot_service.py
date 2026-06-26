import asyncio
import csv
import lzma
import logging
import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import text

from db.db import AsyncSessionLocal
from ip_info_client import IpinfoClient


logger = logging.getLogger("ripe_atlas")


class BRootService:
    """Download and process one B-root data hour into a CSV summary."""

    DATE = "20260407"
    TARGET_HOSTNAME_GROUPS = {
        "AS396982_Google_best": [
            "21.163.120.34.bc.googleusercontent.com",
            "181.246.186.35.bc.googleusercontent.com",
            "203.229.186.35.bc.googleusercontent.com",
        ],
        "AS396982_Google_worst": [
            "157.224.126.34.bc.googleusercontent.com",
            "133.225.126.34.bc.googleusercontent.com",
            "149.233.126.34.bc.googleusercontent.com",
        ],
        "AS16509_Amazon_best": [
            "aa04a9c6947cf3815.awsglobalaccelerator.com",
            "server-13-227-180-243.kix82.r.cloudfront.net",
            "server-13-35-248-201.kix82.r.cloudfront.net",
        ],
        "AS16509_Amazon_worst": [
            "ns-1981.awsdns-55.co.uk",
            "ns-1629.awsdns-11.co.uk",
            "server-52-84-151-179.kix82.r.cloudfront.net",
        ],
        "AS12041_Afilias_best": [
            "v0n1.nic.support",
            "c0.nic.aero",
            "d0.dig.afilias-nst.info",
        ],
        "AS12041_Afilias_worst": [
            "b0.nic.locker",
            "b0.nic.dtv",
            "b0.nic.itv",
        ],
        "AS63911_NetActuate_best": [
            "1.32.225.104.ptr.anycast.net",
            "54.45.54.45.ptr.anycast.net",
            "1.227.53.157.ptr.anycast.net",
        ],
        "AS63911_NetActuate_worst": [
            "ns02.rbxinfra.net",
            "a.portsdns.se",
        ],
        "AS21342_Akamai_best": [
            "n56-a42.aka-ns.net",
            "a23-61-245-128.deploy.static.akamaitechnologies.com",
            "a23-36-65-67.deploy.static.akamaitechnologies.com",
        ],
        "AS21342_Akamai_worst": [
            "a95-100-175-34.deploy.static.akamaitechnologies.com",
            "n3-a20.aka-ns.net",
            "a88-221-81-193.deploy.static.akamaitechnologies.com",
        ],
        "AS42_WoodyNet_best": [
            "nsext-pch.aedns.ae",
            "p.dns.lu",
            "any-ns1.nc",
        ],
        "AS42_WoodyNet_worst": [
            "ns3.protonmail.ch",
        ],
    }
    TARGET_HOSTNAMES = {
        hostname.lower()
        for hostnames in TARGET_HOSTNAME_GROUPS.values()
        for hostname in hostnames
    }
    TARGET_HOSTNAME_METADATA = {}

    for group_name, hostnames in TARGET_HOSTNAME_GROUPS.items():
        asn, provider, case_type = group_name.split("_", 2)
        for hostname in hostnames:
            TARGET_HOSTNAME_METADATA[hostname.lower()] = {
                "asn": asn,
                "provider": provider,
                "case_type": case_type,
            }

    def __init__(
        self,
        db_session_factory=AsyncSessionLocal,
        ipinfo_client_factory=IpinfoClient,
    ) -> None:
        self.project_root = Path(__file__).resolve().parent.parent
        self.base_data_root = self.project_root / "data" / "b-root-analysis"
        self.download_root = self.base_data_root / "downloads"
        self.result_root = self.base_data_root / "results"
        self.db_session_factory = db_session_factory
        self.ipinfo_client_factory = ipinfo_client_factory
        self._db_session = None
        self._ipinfo_client = None

    def download_hour(self, hour: int) -> dict:
        username = os.environ["BROOT_USER"]
        password = os.environ["BROOT_PASSWORD"]

        hour_directory = self._download_hour(hour, username, password)
        downloaded_files = self._get_downloaded_files(hour_directory, hour)
        logger.info(
            "B-root download complete for hour %02d: %d files downloaded",
            hour,
            len(downloaded_files),
        )

        return {
            "hour": hour,
            "date": self.DATE,
            "downloaded_file_count": len(downloaded_files),
            "download_directory": str(hour_directory.relative_to(self.project_root)),
        }

    def process_downloaded_hour(self, hour: int, *, cleanup_downloads: bool = False) -> dict:
        hour_directory = self.download_root / f"{self.DATE}-{hour:02d}"
        downloaded_files = self._get_downloaded_files(hour_directory, hour)

        if not downloaded_files:
            raise FileNotFoundError(
                f"No downloaded files found for hour {hour:02d} in {hour_directory}"
            )

        logger.info(
            "B-root processing start for hour %02d: %d downloaded files found",
            hour,
            len(downloaded_files),
        )
        matches, unique_ip_count, file_summaries = asyncio.run(
            self._collect_matches(downloaded_files)
        )
        output_file = self._write_results(hour, matches)

        if cleanup_downloads:
            self._cleanup_hour_directory(hour_directory)

        return {
            "hour": hour,
            "date": self.DATE,
            "downloaded_file_count": len(downloaded_files),
            "match_count": len(matches),
            "unique_ip_count": unique_ip_count,
            "file_summaries": file_summaries,
            "output_file": str(output_file.relative_to(self.project_root)),
            "downloads_cleaned_up": cleanup_downloads,
        }

    def process_hour(self, hour: int) -> dict:
        self.download_hour(hour)
        return self.process_downloaded_hour(hour, cleanup_downloads=True)

    def _download_hour(self, hour: int, username: str, password: str) -> Path:
        prefix = f"{self.DATE}-{hour:02d}"
        hour_directory = self.download_root / prefix
        hour_directory.mkdir(parents=True, exist_ok=True)
        wget_executable = self._resolve_wget_executable()
        logger.info("Using wget executable: %s", wget_executable)

        command = [
            wget_executable,
            f"--user={username}",
            f"--password={password}",
            "-r",
            "-np",
            "-nH",
            "--cut-dirs=5",
            "-P",
            str(hour_directory),
            "-A",
            f"{prefix}*.fsdb.xz",
            "https://share.ant.isi.edu/tracedist/VTZdSAIrhyGDqkmLS4pm/DITL_B_Root_message_question-20260407/lander_br/",
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as error:
            stderr = (error.stderr or "").strip()
            stdout = (error.stdout or "").strip()
            details = stderr or stdout or "No wget output captured."
            raise RuntimeError(
                f"wget failed with exit code {error.returncode}: {details}"
            ) from error

        return hour_directory

    def _get_downloaded_files(self, hour_directory: Path, hour: int) -> list[Path]:
        if not hour_directory.exists():
            return []
        return list(hour_directory.rglob(f"{self.DATE}-{hour:02d}*.fsdb.xz"))

    def _resolve_wget_executable(self) -> str:
        configured_path = os.getenv("BROOT_WGET_PATH")
        if configured_path and Path(configured_path).exists():
            return configured_path

        for candidate in (
            shutil.which("wget.exe"),
            shutil.which("wget"),
            r"C:\ProgramData\chocolatey\bin\wget.exe",
        ):
            if candidate and Path(candidate).exists():
                return candidate

        raise FileNotFoundError(
            "wget executable not found. Install wget or set BROOT_WGET_PATH to the full wget.exe path."
        )

    async def _lookup_ip_details(self, source_ips: set[str]) -> dict[str, dict[str, str]]:
        if not self._db_session or not self._ipinfo_client:
            raise RuntimeError("Lookup dependencies are not initialized")

        if not source_ips:
            return {}

        ip_details_by_ip = await self._lookup_ip_details_from_db(source_ips)
        missing_ips = [
            ip for ip, details in ip_details_by_ip.items()
            if not details["continent_code"] or not details["country"]
        ]

        if missing_ips:
            fallback_details = await self._lookup_ip_details_from_ipinfo(missing_ips)
            for ip in missing_ips:
                ip_details_by_ip[ip] = {
                    "continent_code": ip_details_by_ip[ip]["continent_code"] or fallback_details[ip]["continent_code"],
                    "country": ip_details_by_ip[ip]["country"] or fallback_details[ip]["country"],
                }

        return ip_details_by_ip

    async def _lookup_ip_details_from_db(self, source_ips: set[str]) -> dict[str, dict[str, str]]:
        ip_list = sorted(source_ips)
        params = {}
        values = []

        for index, ip in enumerate(ip_list):
            placeholder = f"ip_{index}"
            params[placeholder] = ip
            values.append(f"(CAST(:{placeholder} AS inet))")

        query = text(f"""
            WITH ips(ip) AS (
                VALUES {", ".join(values)}
            )
            SELECT DISTINCT ON (ips.ip)
                host(ips.ip) AS source_ip,
                l.continent_code,
                l.country_name
            FROM ips
            LEFT JOIN geoip2_network AS n
                ON n.network >>= ips.ip
            LEFT JOIN geoip2_location AS l
                ON l.geoname_id = n.geoname_id
               AND l.locale_code = 'en'
            ORDER BY ips.ip, masklen(n.network) DESC NULLS LAST
        """)

        result = await self._db_session.execute(query, params)
        rows = result.mappings().all()
        ip_details_by_ip = {
            row["source_ip"]: {
                "continent_code": row["continent_code"] or "",
                "country": row["country_name"] or "",
            }
            for row in rows
        }

        for source_ip in source_ips:
            ip_details_by_ip.setdefault(source_ip, {"continent_code": "", "country": ""})

        return ip_details_by_ip

    async def _lookup_ip_details_from_ipinfo(self, source_ips: list[str]) -> dict[str, dict[str, str]]:
        ip_details_by_ip = {}

        for index, ip in enumerate(sorted(source_ips), start=1):
            try:
                data = await self._ipinfo_client.lookup(ip)
                ip_details_by_ip[ip] = {
                    "continent_code": data.get("continent_code", ""),
                    "country": data.get("country", ""),
                }
            except Exception as error:
                logger.warning("Ipinfo lookup failed for %s: %s", ip, error)
                ip_details_by_ip[ip] = {"continent_code": "", "country": ""}

            if index % 10 == 0 and index < len(source_ips):
                await asyncio.sleep(2)

        return ip_details_by_ip

    async def _collect_matches(
        self,
        downloaded_files: list[Path],
    ) -> tuple[list[dict], int, list[dict]]:
        matches = []
        file_summaries = []
        try:
            async with self.db_session_factory() as session, self.ipinfo_client_factory() as ipinfo:
                self._db_session = session
                self._ipinfo_client = ipinfo

                for filepath in downloaded_files:
                    file_matches = await self._analyze_file(filepath)
                    file_match_count = len(file_matches)
                    logger.info("B-root file %s: %d matches found", filepath.name, file_match_count)
                    file_summaries.append(
                        {
                            "file_name": filepath.name,
                            "match_count": file_match_count,
                        }
                    )
                    matches.extend(file_matches)

                logger.info("B-root total matches across %d files: %d", len(downloaded_files), len(matches))
                return matches, len({match["source_ip"] for match in matches}), file_summaries
        finally:
            self._db_session = None
            self._ipinfo_client = None

    async def _analyze_file(self, filepath: Path) -> list[dict]:
        matches = []
        with lzma.open(filepath, mode="rt", encoding="utf-8", errors="replace") as file:
            for line in file:
                if not line or line.startswith("#"):
                    continue

                fields = line.rstrip("\n").split("\t")

                if len(fields) < 9:
                    continue

                source_ip = fields[2]
                qr = fields[8]
                hostname = fields[-3].lower().rstrip(".")
                query_type = fields[-2]

                if qr == "0" and hostname in self.TARGET_HOSTNAMES:
                    metadata = self.TARGET_HOSTNAME_METADATA[hostname]
                    matches.append(
                        {
                            "hostname": hostname,
                            "source_ip": source_ip,
                            "query_type": query_type,
                            "asn": metadata["asn"],
                            "provider": metadata["provider"],
                            "case_type": metadata["case_type"],
                        }
                    )

        ip_details_by_ip = await self._lookup_ip_details({match["source_ip"] for match in matches})
        for match in matches:
            ip_details = ip_details_by_ip.get(
                match["source_ip"],
                {"continent_code": "", "country": ""},
            )
            match["continent_code"] = ip_details["continent_code"]
            match["country"] = ip_details["country"]

        return matches

    def _write_results(self, hour: int, matches: list[dict]) -> Path:
        self.result_root.mkdir(parents=True, exist_ok=True)
        output_file = self.result_root / f"{self.DATE}-{hour:02d}.csv"

        with output_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "hostname",
                    "source_ip",
                    "query_type",
                    "asn",
                    "provider",
                    "case_type",
                    "continent_code",
                    "country",
                ],
            )
            writer.writeheader()
            writer.writerows(matches)

        return output_file

    def _cleanup_hour_directory(self, hour_directory: Path) -> None:
        for filepath in hour_directory.rglob("*"):
            if filepath.is_file():
                filepath.unlink()

        for directory in sorted(hour_directory.rglob("*"), reverse=True):
            if directory.is_dir():
                directory.rmdir()

        hour_directory.rmdir()
