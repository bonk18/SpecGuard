from fastapi import APIRouter

router= APIRouter(
    prefix="/permits",
    tags=["Permits"]
)

@router.post("/")
def create_permit():
    return {
        "message": "Coming Soon"
    }