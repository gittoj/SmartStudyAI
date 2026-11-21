from fastapi import FastAPI

from app.api import auth, children, dashboard, practice, worksheets

app = FastAPI(title="SmartStudy AI")
for module in (auth, children, worksheets, practice, dashboard):
    app.include_router(module.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
