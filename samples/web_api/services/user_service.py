import structlog

from .external_api import ExternalApiClient

log = structlog.get_logger("UserService")


class UserService:

    def __init__(
            self,
            api: ExternalApiClient,
    ) -> None:
        self._api = api


    async def get_user(self, uid: str) -> dict:

        log.info("user.fetch", uid=uid)

        data = await self._api.get_json("/get")

        return {"uid": uid, "echo": data.get("url")}

