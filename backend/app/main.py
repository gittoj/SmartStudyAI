import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
for module in (auth, children, worksheets, practice, dashboard):
    app.include_router(module.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
