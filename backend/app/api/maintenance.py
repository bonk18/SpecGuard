from fastapi import APIRouter

router= APIRouter(
    prefix="/maintenance",
    tags=["Maintenance"]
)

@router.post("/")
def maintenance_event():
    return {
        "message": "Coming Soon"
    }