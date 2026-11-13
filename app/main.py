"""FastAPI main application."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.redis_client import close_redis
from app.routers import auth, customer, shop, staff, item, card, order, appointment
from app.routers import attendance, commission, revisit, skin_test, message, marketing, report, bookkeeping
from app.routers import inventory as inventory_router
from app.routers import app_setting as app_setting_router
from app.routers import brand as brand_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: create tables (development only)
    await init_db()
    yield
    # Shutdown: close Redis
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="美业门店SaaS管理系统后端API",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(shop.router)
app.include_router(staff.router)
app.include_router(item.router)
app.include_router(card.router)
app.include_router(order.router)
app.include_router(appointment.router)
app.include_router(attendance.router)
app.include_router(commission.router)
app.include_router(revisit.router)
app.include_router(skin_test.router)
app.include_router(message.router)
app.include_router(marketing.router)
app.include_router(report.router)
app.include_router(bookkeeping.router)
app.include_router(inventory_router.router)
app.include_router(app_setting_router.router)
app.include_router(brand_router.router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve test pages (development only)
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/test", StaticFiles(directory=str(_static_dir), html=True), name="test-static")


@app.get("/test-crud")
async def serve_crud_test():
    """Serve CRUD test page."""
    f = _static_dir / "api-test-crud.html"
    if f.exists():
        return FileResponse(str(f), media_type="text/html")
    return {"error": "test page not found"}
