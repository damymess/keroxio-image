from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from typing import Optional

from app.schemas import (
    ProcessRequest,
    ProcessResponse,
    ProcessStatus,
    BackgroundRemovalRequest,
    EnhancementRequest,
)
from app.config import settings
from app.deps import get_current_user

router = APIRouter()


def get_image_service():
    """Get the appropriate image service based on configuration."""
    if settings.AUTOBG_API_KEY:
        # Use AutoBG.ai cloud API
        from app.services.autobg_service import get_autobg_service
        return get_autobg_service()
    else:
        # Fallback to local rembg
        from app.services.birefnet_service import get_birefnet_service
        return get_birefnet_service()


@router.post("/enhance", response_model=ProcessResponse)
async def enhance_image(
    request: EnhancementRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    image_service = Depends(get_image_service),
):
    """
    Enhance image quality.

    Features:
    - Auto color correction
    - Noise reduction
    - Sharpening
    - Contrast boost
    """
    try:
        result = await image_service.enhance_image(
            image_url=request.image_url,
            options={
                "auto_color": request.auto_color,
                "denoise": request.denoise,
                "sharpen": request.sharpen,
                "contrast": getattr(request, "contrast", True),
            },
        )

        return ProcessResponse(
            id=result["id"],
            status="completed",
            original_url=request.image_url,
            processed_url=result["url"],
            processing_time=result.get("processing_time", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhancement failed: {str(e)}",
        )


@router.post("/remove-background", response_model=ProcessResponse)
async def remove_background(
    request: BackgroundRemovalRequest,
    current_user: dict = Depends(get_current_user),
    image_service = Depends(get_image_service),
):
    """
    Remove image background.
    
    Uses AutoBG.ai (if configured) or local rembg.

    Options:
    - Transparent background
    - Solid color background
    - Custom background image
    - Showroom background (virtual car showroom)
    """
    try:
        result = await image_service.remove_background(
            image_url=request.image_url,
            background_type=request.background_type,
            background_color=request.background_color,
            background_url=request.background_url,
        )

        return ProcessResponse(
            id=result["id"],
            status="completed",
            original_url=request.image_url,
            processed_url=result["url"],
            processing_time=result.get("processing_time", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Background removal failed: {str(e)}",
        )


@router.post("/batch", response_model=ProcessResponse)
async def batch_process(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    image_service = Depends(get_image_service),
):
    """
    Process multiple images in batch.

    Returns a job ID that can be used to check status.
    """
    import uuid

    job_id = str(uuid.uuid4())

    # Add to background tasks
    background_tasks.add_task(
        image_service.batch_process,
        job_id=job_id,
        image_urls=request.image_urls,
        operations=request.operations,
        user_id=current_user["id"],
    )

    return ProcessResponse(
        id=job_id,
        status="processing",
        original_url=request.image_urls[0] if request.image_urls else "",
        processed_url=None,
        message=f"Processing {len(request.image_urls)} images",
    )


@router.get("/status/{job_id}", response_model=ProcessStatus)
async def get_process_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the status of a batch processing job."""
    # In a real app, this would check Redis or a database
    return ProcessStatus(
        id=job_id,
        status="processing",
        progress=50,
        total=10,
        completed=5,
        failed=0,
        results=[],
    )


@router.post("/virtual-showroom", response_model=ProcessResponse)
async def virtual_showroom(
    request: BackgroundRemovalRequest,
    current_user: dict = Depends(get_current_user),
    image_service = Depends(get_image_service),
):
    """
    Place vehicle in a virtual showroom environment.

    Available showroom types:
    - indoor: Classic indoor showroom
    - outdoor: Outdoor setting
    - studio: Professional studio
    - custom: Custom background
    """
    try:
        result = await image_service.virtual_showroom(
            image_url=request.image_url,
            showroom_type=request.background_type or "indoor",
        )

        return ProcessResponse(
            id=result["id"],
            status="completed",
            original_url=request.image_url,
            processed_url=result["url"],
            processing_time=result.get("processing_time", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Virtual showroom failed: {str(e)}",
        )


@router.get("/info")
async def service_info():
    """Get information about the image processing service."""
    backend = "autobg-ai" if settings.AUTOBG_API_KEY else "rembg-local"
    return {
        "service": "keroxio-image",
        "backend": backend,
        "features": [
            "background_removal",
            "virtual_showroom",
            "image_enhancement",
            "batch_processing",
        ],
    }
