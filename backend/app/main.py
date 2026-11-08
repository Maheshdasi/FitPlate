import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from . import models  # noqa: F401  (registers tables)
from .config import settings
from .database import Base, engine
from .routers import ai, auth, insights, nutrition, profile, progress, recommendations

logger = logging.getLogger("fitness")

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="AI Fitness & Nutrition Platform API",
    version="1.0.0",
    description="REST API for profiles, calorie targets, food logging, meal and workout "
                "recommendations, progress tracking, weekly insights and the AI assistant.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    """Return validation errors as short, readable messages."""
    errors = []
    for e in exc.errors():
        field = ".".join(str(p) for p in e["loc"] if p not in ("body", "query"))
        msg = e["msg"].removeprefix("Value error, ")
        errors.append({"field": field, "message": msg})
    first = errors[0] if errors else {"field": "", "message": "Invalid input"}
    detail = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
    return JSONResponse(status_code=422,
                        content={"detail": detail, "errors": errors})


@app.exception_handler(IntegrityError)
async def integrity_error(_: Request, exc: IntegrityError):
    logger.warning("Integrity error: %s", exc.orig)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT,
                        content={"detail": "This change conflicts with existing data."})


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "app": "AI Fitness & Nutrition Platform", "docs": "/docs"}


for r in (auth, profile, nutrition, recommendations, progress, insights, ai):
    app.include_router(r.router)
