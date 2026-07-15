from fastapi import APIRouter

router= APIRouter(
    prefix="/cctv-events",
    tags=["CCTV"]
)

@router.post("/")
def cctv_event():
    return {
        "message": "Coming Soon"
    }