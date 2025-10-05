# RIPE IP Geolocation & Measurement Tool

This project provides a FastAPI-based backend and supporting Python modules to automate RIPE Atlas measurements, enrich traceroute data with IP geolocation, and analyze network architecture in specific regions. The tool is designed for researchers, network engineers, and data scientists interested in understanding and visualizing the Internet's structure in targeted areas.

## Features
- **Run RIPE Atlas Measurements:** Initiate and manage measurements using the RIPE Atlas API.
- **Probe Discovery:** Filter and select probes by region or country (e.g., all African probes).
- **Traceroute Parsing:** Parse RIPE Atlas measurement results, including multi-hop traceroutes.
- **IP Enrichment:** Enrich each hop with data from Ipinfo and MaxMind GeoLite2.
- **REST API:** Upload measurement files, trigger new measurements, and retrieve probe lists via HTTP endpoints.
- **CORS Support:** Ready for integration with a separate React frontend.

## Project Structure
```
ripe-ip-geolocation/
├── api.py                  # FastAPI app with all endpoints
├── ripe_atlas_client.py    # Async client for RIPE Atlas API
├── services/
│   └── ripe_atlas_service.py # Service layer for probe/measurement logic
├── ip_info_client.py       # Async client for ipinfo.io
├── geo_lite_client.py      # Async client for MaxMind GeoLite2
├── ripe_measurement_parser.py # Parser for RIPE Atlas measurement files
├── requirements.txt        # Python dependencies
└── ...
```

## Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/ripe-ip-geolocation.git
   cd ripe-ip-geolocation
   ```
2. **Create a virtual environment and activate it:**
   ```sh
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Set up environment variables:**
   - Create a `.env` file in the project root with the following (replace with your actual keys):
     ```env
     IP_INFO_BASE_URL=https://ipinfo.io
     IP_INFO_TOKEN=your_ipinfo_token
     RIPE_ATLAS_BASE_URL=https://atlas.ripe.net/api/v2/
     RIPE_ATLAS_API_KEY=your_ripe_atlas_api_key
     ```

## Running the API
Start the FastAPI server in development mode:
```sh
uvicorn api:app --reload
```
- Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## API Endpoints
- `POST /upload` — Upload a RIPE Atlas measurement file for parsing and enrichment.
- `GET /get_probes` — List all available probes.
- `GET /get_african_probes` — List probes in Africa.
- `GET /initiate_measurement?id=...` — Initiate a new measurement (requires query param).
- `GET /hello` — Health check endpoint.

## Frontend
A separate React frontend (recommended: Vite + React) can be used to interact with this API. CORS is enabled for `localhost:5173` by default.

## License
MIT License

## Acknowledgments
- [RIPE Atlas](https://atlas.ripe.net/)
- [ipinfo.io](https://ipinfo.io/)
- [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)

---
For questions or contributions, please open an issue or pull request.
