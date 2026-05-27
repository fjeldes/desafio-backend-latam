"""
FastAPI application entry point.

This module initializes the FastAPI application, configures the database
via the lifespan handler, sets up request logging and rate limiting
middleware, and registers all user management API routes.

Endpoints
---------
GET  /health        Health check (no rate limit)
GET  /users         List users (paginated, filterable)
POST /users         Create a new user
GET  /users/{id}    Get user by ID
PUT  /users/{id}    Update a user
DELETE /users/{id}  Delete a user
PATCH /users/{id}/deactivate  Deactivate a user
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import engine
from app.limiter import limiter
from app.models import Base
from app.routes import router

# Configure logging level from environment variable, defaulting to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Called when the application starts up: creates all database tables
    defined in the SQLAlchemy metadata if they do not already exist.
    Called again on shutdown for cleanup (no-op in this implementation).
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield


# Create the FastAPI application instance with OpenAPI metadata
app = FastAPI(
    title="User Management API",
    description="RESTful API for user management with full CRUD operations.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting is enabled by default; set RATE_LIMIT_ENABLED=false to disable
if os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false":
    # Store the limiter in app state so SlowAPIMiddleware can find it
    app.state.limiter = limiter
    # Return HTTP 429 with a plain message when a rate limit is exceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # Register rate limiting middleware (must be added before user routes)
    app.add_middleware(SlowAPIMiddleware)

# Register the user management routes under the /users prefix
app.include_router(router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    HTTP middleware that logs every incoming request and its response status.

    Parameters
    ----------
    request : Request
        The incoming HTTP request object.
    call_next : Callable
        The next middleware or route handler in the pipeline.

    Returns
    -------
    Response
        The HTTP response produced by the downstream handler.
    """
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


@app.get("/health", tags=["health"], summary="Health check endpoint")
def health_check():
    """Return a simple health status for monitoring and load balancers."""
    return {"status": "healthy"}
