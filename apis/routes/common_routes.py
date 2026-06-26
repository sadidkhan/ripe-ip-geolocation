import logging

from fastapi import APIRouter, HTTPException, Path

from services.broot_service import BRootService


logger = logging.getLogger("ripe_atlas")

router = APIRouter(prefix="/common", tags=["common"])


@router.post("/broot/download/{hour}")
def download_broot_hour(
    hour: int = Path(..., ge=0, le=23),
):
    """Download one B-root data hour and keep the files on disk."""
    try:
        service = BRootService()
        result = service.download_hour(hour)
        return {
            "status": "success",
            **result,
        }
    except KeyError as error:
        missing_name = error.args[0]
        logger.error("Missing environment variable for B-root download: %s", missing_name)
        raise HTTPException(
            status_code=500,
            detail=f"Missing environment variable: {missing_name}",
        ) from error
    except Exception as error:
        logger.error("Error downloading B-root hour %s: %s", hour, error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/broot/process-downloaded/{hour}")
def process_downloaded_broot_hour(
    hour: int = Path(..., ge=0, le=23),
):
    """Process already-downloaded B-root files for one hour into a CSV file."""
    try:
        service = BRootService()
        result = service.process_downloaded_hour(hour, cleanup_downloads=False)
        return {
            "status": "success",
            **result,
        }
    except KeyError as error:
        missing_name = error.args[0]
        logger.error("Missing environment variable for B-root processing: %s", missing_name)
        raise HTTPException(
            status_code=500,
            detail=f"Missing environment variable: {missing_name}",
        ) from error
    except Exception as error:
        logger.error("Error processing downloaded B-root hour %s: %s", hour, error)
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/broot/run/{hour}")
def run_broot_hour(
    hour: int = Path(..., ge=0, le=23),
):
    """Download and process one B-root data hour into a CSV file, then clean downloads."""
    try:
        service = BRootService()
        result = service.process_hour(hour)
        return {
            "status": "success",
            **result,
        }
    except KeyError as error:
        missing_name = error.args[0]
        logger.error("Missing environment variable for B-root processing: %s", missing_name)
        raise HTTPException(
            status_code=500,
            detail=f"Missing environment variable: {missing_name}",
        ) from error
    except Exception as error:
        logger.error("Error processing B-root hour %s: %s", hour, error)
        raise HTTPException(status_code=500, detail=str(error)) from error
