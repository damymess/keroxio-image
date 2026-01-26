from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import List, Optional
import uuid
from datetime import datetime

from app.schemas import ImageUploadResponse, ImageInfo, ImageListResponse
from app.services.storage import StorageService
from app.deps import get_current_user, get_storage_service

router = APIRouter()

# SECURITY: Magic bytes for image validation
IMAGE_SIGNATURES = {
    b'\xff\xd8\xff': 'jpeg',      # JPEG
    b'\x89PNG\r\n\x1a\n': 'png',  # PNG
    b'RIFF': 'webp',              # WebP (starts with RIFF)
}


def validate_image_content(content: bytes, filename: str) -> Optional[str]:
    """
    Validate image content by checking magic bytes.
    Returns detected extension or None if invalid.
    """
    for signature, ext in IMAGE_SIGNATURES.items():
        if content.startswith(signature):
            return ext
        # Special case for WebP: check for WEBP after RIFF
        if signature == b'RIFF' and len(content) > 12:
            if content[8:12] == b'WEBP':
                return 'webp'
    return None


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Upload a single image."""
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    extension = file.filename.split(".")[-1].lower()
    if extension not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: jpg, jpeg, png, webp",
        )

    # Read file content
    content = await file.read()

    # Check file size (10MB max)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Max size: 10MB",
        )

    # SECURITY: Validate magic bytes to prevent malicious file uploads
    detected_type = validate_image_content(content, file.filename)
    if not detected_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image content. File does not match a valid image format.",
        )

    # Use detected type for filename (more secure than trusting extension)
    actual_extension = "jpg" if detected_type == "jpeg" else detected_type

    # Generate unique filename
    image_id = str(uuid.uuid4())
    filename = f"{current_user['id']}/{image_id}.{actual_extension}"

    # Upload to storage
    url = await storage.upload(filename, content, file.content_type or "image/jpeg")

    return ImageUploadResponse(
        id=image_id,
        url=url,
        filename=file.filename,
        size=len(content),
        content_type=file.content_type or "image/jpeg",
        created_at=datetime.utcnow(),
    )


@router.post("/upload-multiple", response_model=List[ImageUploadResponse])
async def upload_multiple_images(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Upload multiple images at once."""
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 images per request",
        )

    results = []
    for file in files:
        if not file.filename:
            continue

        extension = file.filename.split(".")[-1].lower()
        if extension not in ["jpg", "jpeg", "png", "webp"]:
            continue

        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            continue

        # SECURITY: Validate magic bytes
        detected_type = validate_image_content(content, file.filename)
        if not detected_type:
            continue

        actual_extension = "jpg" if detected_type == "jpeg" else detected_type
        image_id = str(uuid.uuid4())
        filename = f"{current_user['id']}/{image_id}.{actual_extension}"

        url = await storage.upload(filename, content, file.content_type or "image/jpeg")

        results.append(
            ImageUploadResponse(
                id=image_id,
                url=url,
                filename=file.filename,
                size=len(content),
                content_type=file.content_type or "image/jpeg",
                created_at=datetime.utcnow(),
            )
        )

    return results


@router.get("/{image_id}", response_model=ImageInfo)
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Get image information by ID."""
    # In a real app, this would query a database
    # For now, we return a placeholder
    return ImageInfo(
        id=image_id,
        url=f"https://images.keroxio.fr/{current_user['id']}/{image_id}.jpg",
        processed=False,
        created_at=datetime.utcnow(),
    )


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
):
    """Delete an image."""
    # Delete from storage
    filename = f"{current_user['id']}/{image_id}"
    await storage.delete(filename)

    return {"message": "Image deleted successfully"}


@router.get("/", response_model=ImageListResponse)
async def list_images(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """List user's images."""
    # In a real app, this would query a database
    return ImageListResponse(
        images=[],
        total=0,
        page=page,
        limit=limit,
    )
