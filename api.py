from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
from geo_lite_client import GeoLiteClient
from ip_info_client import IpinfoClient
from ripe_atlas_client import RipeAtlasClient
from ripe_measurement_parser import RipeMeasurementParser
from dotenv import load_dotenv

from services.ripe_atlas_service import RipeAtlasService

load_dotenv()
# Import your IpinfoClient and GeoLiteClient here
# from ip_info_client import IpinfoClient
# from geo_lite_client import GeoLiteClient

app = FastAPI()

# Frontend origin(s)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # don't use "*" if you need cookies
    allow_credentials=True,         # set to False if not using cookies/auth
    allow_methods=["POST", "OPTIONS"],  # or ["*"] during dev
    allow_headers=["*"],            # or list explicitly: ["content-type", "authorization"]
)


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

@app.get("/get_african_probes")
async def get_african_probes():
    service = RipeAtlasService()
    probes = await service.get_probes_from_Africa()
    return {"probes": probes}
