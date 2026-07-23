from typing import Annotated

from app.container import AppContainer
from app.services.user_service import UserService
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{uid}")
@inject
async def get_user(
    uid: str,
    svc: Annotated[UserService, Depends(Provide[AppContainer.user_service])],
):

    return await svc.get_user(uid)


