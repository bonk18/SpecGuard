from fastapi import APIRouter

router= APIRouter(
    prefix="/interventions",
    tags=["Interventions"]
)

@router.get("/")
def get_interventions():
    return {
        "message": "Coming Soon"
    }