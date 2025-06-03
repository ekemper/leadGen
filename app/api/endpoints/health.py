from fastapi import APIRouter, status

router = APIRouter()

@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy", "service": "fastapi-k8-proto"}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    # TODO: Add database and Redis connectivity checks
    return {"status": "ready"}

@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    return {"status": "alive"} 