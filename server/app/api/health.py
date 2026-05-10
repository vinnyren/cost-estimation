from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"ok": True, "service": "cost-estimation", "version": "1.0.0"}
