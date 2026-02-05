from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
from anycast_ip_collection import get_anycast_ips
from geo_lite_client import GeoLiteClient
from ip_info_client import IpinfoClient
from logging_config import setup_logger
from ripe_atlas_client import RipeAtlasClient
from ripe_measurement_parser import RipeMeasurementParser
from dotenv import load_dotenv

from services.ripe_atlas_service import RipeAtlasService

# Import routers
from apis.routes import measurement_router, probe_router

load_dotenv()
logger = setup_logger()

app = FastAPI(title="RIPE IP Geolocation API")

# CORS middleware
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(measurement_router)
app.include_router(probe_router)


@app.get("/")
def home():
    return RedirectResponse(url="/hello")

@app.get("/hello")
def hello():
    return {"message": "Hello, world!"}

@app.post("/upload")
async def upload_measurement(file: UploadFile = File(...)):
    # Save uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    parser = RipeMeasurementParser(tmp_path)
    measurements = parser.parse_measurements()

    async with IpinfoClient() as ipinfo, GeoLiteClient() as geolite:
        for measurement in measurements:
            for trace in measurement["traceroute"]:
                ip = trace["from"]
                if ip == "*" or ip is None:
                    trace["ipinfo"] = None
                    trace["geolite"] = None
                    continue
                ipinfo_data = await ipinfo.lookup(ip)

                try:
                    geolite_data = await geolite.city(ip)
                except Exception as e:
                    print(f"Error fetching GeoLite data for {ip}: {e}")
                    geolite_data = {}

                trace["ipinfo"] = ipinfo_data
                trace["geolite"] = geolite_data

    return measurements


@app.get("/initiate_measurement")
async def initiate_measurement():
    service = RipeAtlasService()
    result = await service.initiate_measurement()
    return {"result": result}


@app.get("/process_measurement_results")
async def process_measurement_results():
    service = RipeAtlasService()
    result = await service.process_ping_msm_results()
    return {"result": result}


@app.get("/get_anycast_ip_details")
async def get_anycast_ip_details():
    service = RipeAtlasService()
    result = await service.get_anycast_ip_details()
    return {"result": result}
