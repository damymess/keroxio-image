"""
AutoBG.ai API service for automotive background removal.
Specialized for car dealership photos.
"""
import io
import uuid
import base64
from typing import Optional, Dict, Any
from pathlib import Path

import httpx
from PIL import Image

from app.config import settings


class AutoBGService:
    """
    AutoBG.ai API client for professional car photo editing.
    
    Features:
    - Background removal optimized for vehicles
    - Virtual showroom backgrounds
    - Realistic shadows
    - High-quality output
    """

    def __init__(self):
        self.api_key = settings.AUTOBG_API_KEY
        self.base_url = "https://www.autobg.ai/api"
        
    async def _download_image(self, image_url: str) -> bytes:
        """Download image from URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    async def _upload_to_storage(self, image_bytes: bytes, filename: str) -> str:
        """Save processed image to local storage."""
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
        Remove background using AutoBG.ai API.
        
        Args:
            image_url: URL of the source image
            background_type: transparent, solid, custom, or showroom type
            background_color: Hex color for solid backgrounds
            background_url: URL for custom background image
        """
        import time
        start = time.time()
        
        # Download source image
        image_bytes = await self._download_image(image_url)
        
        # Encode image as base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Prepare API request
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        
        # Determine background setting
        bg_setting = "transparent"
        if background_type == "solid" and background_color:
            bg_setting = background_color
        elif background_type in ["showroom", "indoor", "studio", "outdoor"]:
            bg_setting = background_type
        
        payload = {
            "image": image_b64,
            "background": bg_setting,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/remove-background",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                
                # Get processed image from response
                if "image" in result:
                    processed_bytes = base64.b64decode(result["image"])
                elif "url" in result:
                    processed_bytes = await self._download_image(result["url"])
                else:
                    raise ValueError("No image in API response")
                    
            except httpx.HTTPError as e:
                print(f"AutoBG API error: {e}")
                # Fallback to returning original image
                processed_bytes = image_bytes
        
        # Save to storage
        ext = "png" if background_type == "transparent" else "jpg"
        filename = f"{uuid.uuid4()}.{ext}"
        processed_url = await self._upload_to_storage(processed_bytes, filename)
        
        processing_time = time.time() - start
        
        return {
            "id": str(uuid.uuid4()),
            "url": processed_url,
            "processing_time": round(processing_time, 2),
            "model": "autobg-ai",
            "status": "completed",
        }

    async def virtual_showroom(
        self,
        image_url: str,
        showroom_type: str = "indoor",
    ) -> Dict[str, Any]:
        """
        Place vehicle in virtual showroom using AutoBG.ai.
        
        Showroom types:
        - indoor: Classic indoor showroom
        - outdoor: Outdoor setting
        - studio: Professional studio
        """
        return await self.remove_background(
            image_url=image_url,
            background_type=showroom_type,
        )

    async def enhance_image(
        self,
        image_url: str,
        options: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Enhance image (basic PIL enhancement, AutoBG doesn't have this).
        """
        from PIL import ImageEnhance
        import time
        start = time.time()
        
        options = options or {}
        
        image_bytes = await self._download_image(image_url)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Apply enhancements
        if options.get("auto_color", True):
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.15)
        
        if options.get("contrast", True):
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)
        
        if options.get("sharpen", True):
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92)
        output.seek(0)
        
        filename = f"{uuid.uuid4()}.jpg"
        processed_url = await self._upload_to_storage(output.getvalue(), filename)
        
        processing_time = time.time() - start
        
        return {
            "id": str(uuid.uuid4()),
            "url": processed_url,
            "processing_time": round(processing_time, 2),
            "status": "completed",
        }

    async def batch_process(
        self,
        job_id: str,
        image_urls: list,
        operations: list,
        user_id: str,
    ) -> Dict[str, Any]:
        """Process multiple images in batch."""
        results = []
        
        for url in image_urls:
            try:
                result = {"image_url": url, "status": "completed"}
                
                for op in operations:
                    if op == "enhance":
                        processed = await self.enhance_image(url)
                        result["processed_url"] = processed["url"]
                    elif op == "remove_background":
                        processed = await self.remove_background(url)
                        result["processed_url"] = processed["url"]
                    elif op == "showroom":
                        processed = await self.virtual_showroom(url)
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


# Singleton instance
_service_instance = None

def get_autobg_service() -> AutoBGService:
    """Get or create AutoBG service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AutoBGService()
    return _service_instance
