from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import auth, crews, imports, routes, stops

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="İbnüssebil API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}


app.include_router(auth.router, prefix="/api")
app.include_router(crews.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(stops.router, prefix="/api")
app.include_router(routes.router, prefix="/api")


_WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
if _WEB_DIST.exists():
    assets_dir = _WEB_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        candidate = _WEB_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_WEB_DIST / "index.html", headers={"Cache-Control": "no-cache"})
