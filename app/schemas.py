from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BackgroundType(str, Enum):
    TRANSPARENT = "transparent"
    SOLID = "solid"
    SHOWROOM = "showroom"
    CUSTOM = "custom"


# Upload schemas
class ImageUploadResponse(BaseModel):
    id: str
    url: str
    filename: str
    size: int
    content_type: str
    created_at: datetime


class ImageInfo(BaseModel):
    id: str
    url: str
    processed: bool = False
    processed_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ImageListResponse(BaseModel):
    images: List[ImageInfo]
    total: int
    page: int
    limit: int


# Processing schemas
class EnhancementRequest(BaseModel):
    image_url: str
    auto_color: bool = True
    denoise: bool = True
    sharpen: bool = True
    hdr: bool = False


class BackgroundRemovalRequest(BaseModel):
    image_url: str
    background_type: Optional[str] = "transparent"
    background_color: Optional[str] = None
    background_url: Optional[str] = None


class ProcessRequest(BaseModel):
    image_urls: List[str]
    operations: List[str] = Field(
        default=["enhance"],
        description="Operations to perform: enhance, remove_background, showroom",
    )


class ProcessResponse(BaseModel):
    id: str
    status: str
    original_url: str
    processed_url: Optional[str] = None
    processing_time: Optional[float] = None
    message: Optional[str] = None


class ProcessResult(BaseModel):
    image_url: str
    processed_url: Optional[str] = None
    status: str
    error: Optional[str] = None


class ProcessStatus(BaseModel):
    id: str
    status: str
    progress: int = 0
    total: int = 0
    completed: int = 0
    failed: int = 0
    results: List[ProcessResult] = []
