from fastapi import APIRouter

router = APIRouter(prefix="/ai", tags=["Health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "memora-ai"}
