from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import images, process


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.SERVICE_NAME}...")
    
    # Ensure storage directories exist
    storage_path = Path(settings.STORAGE_PATH)
    (storage_path / "processed").mkdir(parents=True, exist_ok=True)
    (storage_path / "uploads").mkdir(parents=True, exist_ok=True)
    print(f"📁 Storage path: {storage_path}")
    
    yield
    # Shutdown
    print(f"Shutting down {settings.SERVICE_NAME}...")


app = FastAPI(
    title="Keroxio Image Service",
    description="Image upload, processing and enhancement service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - uses CORS_ORIGINS env var in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
)

# Routers
app.include_router(images.router, prefix="/images", tags=["Images"])
app.include_router(process.router, prefix="/process", tags=["Processing"])

# Static files for processed images (local storage)
storage_path = Path(settings.STORAGE_PATH)
if storage_path.exists():
    app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")


@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
