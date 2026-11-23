import asyncio
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import auth, children, dashboard, practice, worksheets
from app.services.rate_limit_service import purge_old_events
from app.services.worksheet_service import purge_expired_files, recover_stuck_worksheets

logger = logging.getLogger(__name__)


async def _purge_loop() -> None:
    while True:
        try:
            await purge_expired_files()
        except Exception as error:
            logger.error("purge failed error=%s", type(error).__name__)
        await asyncio.sleep(3600)


async def _sweep_loop() -> None:
    """Recover abandoned worksheets right away (a restart is the usual cause), then keep checking."""
    while True:
        try:
            recovered = await recover_stuck_worksheets()
            if recovered:
                logger.warning("sweep recovered=%s", recovered)
            await purge_old_events()
        except Exception as error:
            logger.error("sweep failed error=%s", type(error).__name__)
        await asyncio.sleep(settings.sweep_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    tasks = [asyncio.create_task(_purge_loop()), asyncio.create_task(_sweep_loop())]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="SmartStudy AI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


PROXY_SECRET_HEADER = "x-proxy-secret"
OPEN_PATHS = {"/health"}


@app.middleware("http")
async def require_proxy_secret(request: Request, call_next):
    """With PROXY_SHARED_SECRET set, only requests forwarded by the Next.js proxy are served.
    This also makes the client-IP header that the proxy sets trustworthy for rate limiting."""
    expected = settings.proxy_shared_secret
    if expected and request.url.path not in OPEN_PATHS and request.method != "OPTIONS":
        supplied = request.headers.get(PROXY_SECRET_HEADER, "")
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            return JSONResponse({"detail": "Not found."}, status_code=404)
    return await call_next(request)


for module in (auth, children, worksheets, practice, dashboard):
    app.include_router(module.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
