from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
from typing import List, Dict, Any
from anycast_ip_collection import get_anycast_ips
from geo_lite_client import GeoLiteClient
from ip_info_client import IpinfoClient
from logging_config import setup_logger
from ripe_atlas_client import RipeAtlasClient
from ripe_measurement_parser import RipeMeasurementParser
from dotenv import load_dotenv

from services.ripe_atlas_service import RipeAtlasService
from db.db import check_db_connection, get_db, AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Import routers
from apis.routes import anycast_router, common_router, measurement_router, probe_router

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
app.include_router(common_router)


@app.get("/")
def home():
    return RedirectResponse(url="/docs")

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


# ============================================
# NEW DATABASE ENDPOINTS
# ============================================

@app.get("/health/db")
async def health_check_db() -> Dict[str, Any]:
    """Check database connection status"""
    is_connected = await check_db_connection()
    return {
        "status": "healthy" if is_connected else "unhealthy",
        "database": "PostgreSQL",
        "connected": is_connected
    }


@app.get("/api/db/tables")
async def get_database_tables(session: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get list of all tables in the database"""
    try:
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        result = await session.execute(query)
        tables = [row[0] for row in result.fetchall()]
        
        return {
            "status": "success",
            "table_count": len(tables),
            "tables": tables
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/db/stats")
async def get_database_stats(session: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get database statistics including table row counts"""
    try:
        query = text("""
            SELECT 
                table_name,
                (xpath('/row/cnt/text()', 
                    xml_count))[1]::text::int AS row_count
            FROM (
                SELECT
                    table_name,
                    query_to_xml(format('SELECT count(*) AS cnt FROM %I.%I', 
                        table_schema, table_name), false, true, '') AS xml_count
                FROM information_schema.tables
                WHERE table_schema = 'public'
            ) t
            ORDER BY row_count DESC
        """)
        result = await session.execute(query)
        stats = [{"table": row[0], "row_count": row[1]} for row in result.fetchall()]
        
        total_rows = sum(stat["row_count"] for stat in stats)
        
        return {
            "status": "success",
            "total_tables": len(stats),
            "total_rows": total_rows,
            "tables": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/api/db/query")
async def execute_custom_query(query_data: Dict[str, str], session: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Execute a custom SQL SELECT query (read-only)"""
    try:
        sql_query = query_data.get("query", "").strip()
        
        # Security: Only allow SELECT queries
        if not sql_query.upper().startswith("SELECT"):
            return {
                "status": "error",
                "message": "Only SELECT queries are allowed"
            }
        
        result = await session.execute(text(sql_query))
        rows = result.fetchall()
        
        return {
            "status": "success",
            "row_count": len(rows),
            "data": [dict(row._mapping) for row in rows] if rows else []
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

