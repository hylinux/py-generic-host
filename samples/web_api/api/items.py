from fastapi import APIRouter

router = APIRouter(
    prefix="/items",
    tags=["items"],
)

@router.get("/")
async def list_items():
    return [
        {
            "id": 1,
            "name": "demo",
        }
    ]
