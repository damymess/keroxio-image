"""
Fallback image processing service (when AutoBG.ai is not configured).
Uses basic PIL operations only.
"""
import io
import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance, ImageFilter

from app.config import settings


class BiRefNetService:
    """
    Fallback image processing service using PIL only.
    
    For full background removal, configure AUTOBG_API_KEY.
    """

    def __init__(self):
        self._backgrounds = {
            "white": "#FFFFFF",
            "gray": "#808080",
            "dark": "#1f2937",
            "showroom": "#2d3748",
        }
        print("⚠️ Using fallback PIL service. Configure AUTOBG_API_KEY for background removal.")

    async def _download_image(self, image_url: str) -> bytes:
        """Download image from URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    async def _upload_image(self, image_bytes: bytes, filename: str) -> str:
        """Upload processed image to storage."""
        storage_path = Path(settings.STORAGE_PATH) / "processed"
        storage_path.mkdir(parents=True, exist_ok=True)
        
        file_path = storage_path / filename
        file_path.write_bytes(image_bytes)
        
        return f"{settings.STORAGE_URL}/processed/{filename}"

    async def remove_background(
        self,
        image_url: str,
        background_type: str = "transparent",
        background_color: Optional[str] = None,
        background_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fallback: returns original image with a warning.
        Configure AUTOBG_API_KEY for real background removal.
        """
        import time
        start = time.time()
        
        # Just return the original image with enhancement
        image_bytes = await self._download_image(image_url)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Apply basic enhancement
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92)
        output.seek(0)
        
        filename = f"{uuid.uuid4()}.jpg"
        processed_url = await self._upload_image(output.getvalue(), filename)
        
        processing_time = time.time() - start
        
        return {
            "id": str(uuid.uuid4()),
            "url": processed_url,
            "processing_time": round(processing_time, 2),
            "model": "fallback-pil",
            "status": "completed",
            "warning": "Background removal requires AUTOBG_API_KEY",
        }

    async def enhance_image(
        self,
        image_url: str,
        options: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """Enhance image using PIL."""
        import time
        start = time.time()
        
        options = options or {}
        
        image_bytes = await self._download_image(image_url)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        if options.get("auto_color", True):
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.15)
        
        if options.get("contrast", True):
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)
        
        if options.get("denoise", False):
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        if options.get("sharpen", True):
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92)
        output.seek(0)
        
        filename = f"{uuid.uuid4()}.jpg"
        processed_url = await self._upload_image(output.getvalue(), filename)
        
        processing_time = time.time() - start
        
        return {
            "id": str(uuid.uuid4()),
            "url": processed_url,
            "processing_time": round(processing_time, 2),
            "status": "completed",
        }

    async def virtual_showroom(
        self,
        image_url: str,
        showroom_type: str = "indoor",
    ) -> Dict[str, Any]:
        """Fallback: just enhance the image."""
        return await self.enhance_image(image_url)

    async def batch_process(
        self,
        job_id: str,
        image_urls: List[str],
        operations: List[str],
        user_id: str,
    ) -> Dict[str, Any]:
        """Process multiple images in batch."""
        results = []
        
        for url in image_urls:
            try:
                result = {"image_url": url, "status": "completed"}
                processed = await self.enhance_image(url)
                result["processed_url"] = processed["url"]
                results.append(result)
            except Exception as e:
                results.append({
                    "image_url": url,
                    "status": "failed",
                    "error": str(e),
                })
        
        return {
            "job_id": job_id,
            "status": "completed",
            "results": results,
        }


_service_instance = None

def get_birefnet_service() -> BiRefNetService:
    """Get or create service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = BiRefNetService()
    return _service_instance
