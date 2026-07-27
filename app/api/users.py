from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.container import AppContainer
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{uid}")
@inject
async def get_user(
    uid: str,
    svc: Annotated[UserService, Depends(Provide[AppContainer.user_service])],
):

    return await svc.get_user(uid)


