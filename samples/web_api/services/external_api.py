import httpx
import structlog
from samples.web_api.settings import ExternalApiSettings

from py_generic_host.resilience.retry import default_retry

log = structlog.get_logger("ExternalApi")


class ExternalApiClient:

    def __init__(
            self,
            client: httpx.AsyncClient,
            options: ExternalApiSettings,
    ) -> None:

        self._client = client
        self._opts = options


    @default_retry(
        exc_types=(httpx.HTTPError,),
        attempts=3
    )
    async def get_json(
        self,
        path: str,
    ) -> dict:
        opts = self._opts
        url = f"{opts.base_url}{path}"

        log.info("external.request", url=url)

        resp = await self._client.get(url, timeout=opts.timeout)
        resp.raise_for_status()

        return resp.json()


    async def ping(self) -> bool: 
        try:
            await self.get_json("/status/200")
            return True
        except Exception:
            return False

