"""FastAPI application with refactored architecture."""
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from logging_config import setup_logger

# Import routers
from api.routes import measurement_router, probe_router, anycast_router

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
app.include_router(anycast_router)


@app.get("/")
def home():
    """Redirect to /hello."""
    return RedirectResponse(url="/hello")


@app.get("/hello")
def hello():
    """Simple hello endpoint."""
    return {"message": "Hello, world! RIPE IP Geolocation API is running."}


# Legacy endpoints for backwards compatibility
# These now use the new architecture under the hood

@app.get("/initiate_measurement")
async def initiate_measurement_legacy():
    """Legacy endpoint - redirects to new endpoint."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=301,
        content={"message": "Please use POST /measurements/initiate instead"},
        headers={"Location": "/measurements/initiate"}
    )


@app.get("/process_measurement_results")
async def process_measurement_results_legacy():
    """Legacy endpoint - redirects to new endpoint."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=301,
        content={"message": "Please use POST /measurements/process-results instead"},
        headers={"Location": "/measurements/process-results"}
    )


@app.get("/get_anycast_ip_details")
async def get_anycast_ip_details_legacy():
    """Legacy endpoint - redirects to new endpoint."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=301,
        content={"message": "Please use POST /anycast/enrich instead"},
        headers={"Location": "/anycast/enrich"}
    )

