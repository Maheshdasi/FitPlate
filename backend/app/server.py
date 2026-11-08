"""
Production entry point: one server for the whole platform.

  /api/...   the FastAPI backend (Swagger docs at /api/docs)
  /...       the built React website (frontend/dist)

Used by the Dockerfile for online hosting (e.g. Render). For local development
keep using `uvicorn app.main:app` together with `npm run dev`.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import PROJECT_ROOT
from .database import Base, engine
from .main import app as api

DIST = (PROJECT_ROOT / "frontend" / "dist").resolve()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Mounted apps don't run their own startup, so create the tables here
    Base.metadata.create_all(bind=engine)
    yield


site = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
site.mount("/api", api)

if (DIST / "assets").is_dir():
    site.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@site.get("/{path:path}", include_in_schema=False)
def website(path: str):
    """Serve a built file if it exists, otherwise the React app (it handles its own routes)."""
    if not (DIST / "index.html").is_file():
        raise HTTPException(503, "Website not built. Run `npm run build` in the frontend folder.")
    file = (DIST / path).resolve()
    if path and file.is_file() and DIST in file.parents:
        return FileResponse(file)
    return FileResponse(DIST / "index.html")
