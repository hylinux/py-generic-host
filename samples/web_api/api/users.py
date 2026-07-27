from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from samples.web_api.container import AppContainer
from samples.web_api.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{uid}")
@inject
async def get_user(
    uid: str,
    svc: Annotated[UserService, Depends(Provide[AppContainer.user_service])],
):

    return await svc.get_user(uid)


