import logging
from time import perf_counter
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError
from starlette.responses import JSONResponse
from database import get_db
import rate_limit
from routers.dashboard import router as dashboard_router
from web_config import ALLOWED_ORIGINS
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from routers.auth import router as auth_router
from routers.relationships import router as relationships_router
from routers.journal_entries import router as journal_entries_router

app = FastAPI(
    title="Relationship Journal API",
    description="A private relationship and journal management API.",
    version="1.0.0"
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    errors = [
        {
            "loc": error["loc"],
            "type": error["type"],
            "msg": "Invalid input"
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={"detail": errors}
    )


app.include_router(auth_router)
app.include_router(relationships_router)
app.include_router(journal_entries_router)

app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type"])
app.include_router(dashboard_router)
logger = logging.getLogger("uvicorn.error")

@app.middleware("http")
async def safe_request_logging(request, call_next):
    start = perf_counter()
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    logger.info("method=%s status=%s duration_ms=%.1f", request.method,
                response.status_code, (perf_counter() - start) * 1000)
    return response

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}

@app.get("/ready", tags=["system"])
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        rate_limit.redis_client.ping()
    except (SQLAlchemyError, RedisError):
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}
