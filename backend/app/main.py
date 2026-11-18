"""FastAPI application factory and entrypoint."""

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings, validate_security
from app.core.limiter import limiter
from app.core.logging import configure_logging, get_logger
from app.core.request_context import RequestContext, reset_request_context, set_request_context
from app.db.session import run_migrations, SessionLocal
from app.api.routers import (
    admin,
    admin_scheduling,
    analytics,
    attendance,
    auth,
    face,
    liveness,
    users,
    user_scheduling,
)

configure_logging()
logger = get_logger("smart_attendance")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on insecure production configuration.
    validate_security(settings)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.DATASET_DIR, exist_ok=True)
    run_migrations()
    logger.info(f"{settings.PROJECT_NAME} v{settings.API_VERSION} started")
    # Effective AI/ML configuration in one line, so an operator can tell from
    # the logs exactly which gallery and liveness rules a process is running
    # (thresholds and the direction-sign calibration are easy to mis-set per
    # environment and otherwise invisible until a match fails).
    logger.info(
        "Face/liveness config: "
        f"model_pack={settings.FACE_MODEL_PACK} "
        f"match_threshold={settings.FACE_MATCH_THRESHOLD} "
        f"duplicate_threshold={settings.FACE_DUPLICATE_THRESHOLD} "
        f"min_confidence={settings.FACE_ATTENDANCE_MIN_CONFIDENCE} "
        f"liveness_challenge={settings.LIVENESS_CHALLENGE_ENABLED} "
        f"min_yaw_sweep={settings.LIVENESS_MIN_YAW_SWEEP} "
        f"require_direction={settings.LIVENESS_REQUIRE_DIRECTION} "
        f"direction_sign={settings.LIVENESS_DIRECTION_SIGN:+d} "
        f"enforce_planarity={settings.LIVENESS_ENFORCE_PLANARITY}"
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        # Correlation id: accept a caller-supplied one (sanitized), otherwise
        # generate. Exposed back on the response and injected into every log
        # line and audit record for this request.
        incoming = request.headers.get(settings.REQUEST_ID_HEADER, "")
        request_id = incoming.strip()[:128] if incoming.strip() else uuid.uuid4().hex
        client_host = request.client.host if request.client else None
        token = set_request_context(
            RequestContext(
                request_id=request_id,
                ip_address=client_host,
                user_agent=request.headers.get("user-agent"),
            )
        )
        try:
            response = await call_next(request)
        finally:
            reset_request_context(token)
        response.headers[settings.REQUEST_ID_HEADER] = request_id
        return response

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Error handling ───────────────────────────────────────────────────
    # Unhandled exceptions must not echo internal details (exception text, SQL,
    # file paths) back to the client. The full traceback is logged server-side;
    # the response carries a generic message.

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning(f"Integrity error on {request.method} {request.url.path}", exc_info=exc)
        return JSONResponse(
            status_code=409,
            content={"detail": "That change conflicts with an existing record."},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database error on {request.method} {request.url.path}", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "A database error occurred. Please try again."},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Please try again."},
        )

    @app.get("/", tags=["health"])
    async def root():
        return {"message": f"{settings.PROJECT_NAME} API", "version": settings.API_VERSION}

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["health"])
    async def ready():
        """
        Readiness probe: verifies the process can reach the database.

        `/health` only proves the process is up; `/ready` proves it can serve
        traffic. Returns 503 so orchestrators and load balancers route away
        from an instance whose DB is unavailable.
        """
        try:
            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
            finally:
                db.close()
        except Exception:
            logger.exception("Readiness check failed: database unreachable")
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "detail": "Database unreachable."},
            )
        return {"status": "ready"}

    for router in (
        auth.router,
        face.router,
        liveness.router,
        attendance.router,
        users.router,
        user_scheduling.router,
        admin.router,
        admin_scheduling.router,
        analytics.router,
    ):
        app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
