"""
Rembg-based image processing service.
Free, self-hosted background removal using U2Net.
"""
import io
import uuid
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance, ImageFilter
from rembg import remove, new_session

from app.config import settings


class RembgService:
    """Free self-hosted image processing using rembg + PIL."""

    def __init__(self):
        # Initialize rembg session (loads model once)
        self.session = new_session("u2net")
        self._backgrounds = {
            "white": "#FFFFFF",
            "gray": "#808080",
            "dark": "#1f2937",
            "showroom": "#2d3748",
        }

    async def _download_image(self, image_url: str) -> bytes:
        """Download image from URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    async def _upload_image(self, image_bytes: bytes, filename: str) -> str:
        """
        Upload processed image to storage.
        Returns the public URL.
        """
        # In production, upload to R2/S3
        # For now, save locally and return path
        storage_path = Path(settings.STORAGE_PATH) / "processed"
        storage_path.mkdir(parents=True, exist_ok=True)
        
        file_path = storage_path / filename
        file_path.write_bytes(image_bytes)
        
        # Return URL (adjust based on your storage setup)
        return f"{settings.STORAGE_URL}/processed/{filename}"

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    async def remove_background(
        self,
        image_url: str,
        background_type: str = "transparent",
        background_color: Optional[str] = None,
        background_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Remove image background using rembg (free, local).
        
        Types:
        - transparent: PNG with alpha
        - solid: Solid color background
        - custom: Custom background image
        """
        import time
        start = time.time()
        
        # Download source image
        image_bytes = await self._download_image(image_url)
        
        # Remove background using rembg
        result_bytes = await asyncio.to_thread(
            remove,
            image_bytes,
            session=self.session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
        )
        
        # Open as PIL Image
        result_image = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        
        # Apply background based on type
        if background_type == "solid" and background_color:
            # Create solid color background
            bg_color = self._hex_to_rgb(background_color)
            background = Image.new("RGBA", result_image.size, bg_color + (255,))
            background.paste(result_image, mask=result_image.split()[3])
            result_image = background.convert("RGB")
            
        elif background_type == "custom" and background_url:
            # Use custom background image
            bg_bytes = await self._download_image(background_url)
            background = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
            background = background.resize(result_image.size, Image.Resampling.LANCZOS)
            background.paste(result_image, mask=result_image.split()[3])
            result_image = background.convert("RGB")
            
        elif background_type in self._backgrounds:
            # Preset background
            bg_color = self._hex_to_rgb(self._backgrounds[background_type])
            background = Image.new("RGBA", result_image.size, bg_color + (255,))
            background.paste(result_image, mask=result_image.split()[3])
            result_image = background.convert("RGB")
        
        # Save result
        output = io.BytesIO()
        if background_type == "transparent":
            result_image.save(output, format="PNG", optimize=True)
            ext = "png"
        else:
            result_image.convert("RGB").save(output, format="JPEG", quality=90)
            ext = "jpg"
        
        output.seek(0)
        
        # Upload to storage
        filename = f"{uuid.uuid4()}.{ext}"
        processed_url = await self._upload_image(output.getvalue(), filename)
        
        processing_time = time.time() - start
        
        return {
            "id": str(uuid.uuid4()),
            "url": processed_url,
            "processing_time": round(processing_time, 2),
            "status": "completed",
        }

    async def enhance_image(
        self,
        image_url: str,
        options: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Enhance image using PIL (free).
        
        Options:
        - auto_color: Color enhancement
        - denoise: Blur for noise reduction
        - sharpen: Sharpening
        - contrast: Contrast boost
        """
        import time
        start = time.time()
        
        options = options or {}
        
        # Download image
        image_bytes = await self._download_image(image_url)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Apply enhancements
        if options.get("auto_color", True):
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.15)  # Slight color boost
        
        if options.get("contrast", True):
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)  # Slight contrast boost
        
        if options.get("denoise", False):
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        if options.get("sharpen", True):
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)  # Sharpen
        
        # Auto brightness
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        # Save result
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92)
        output.seek(0)
        
        # Upload
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
        """
        Place vehicle on showroom background.
        Uses pre-made showroom backgrounds.
        """
        # Map showroom types to background colors/images
        showroom_backgrounds = {
            "indoor": "#1a1a2e",
            "outdoor": "#87CEEB",
            "studio": "#2d3748",
            "dark": "#0f0f0f",
            "white": "#f8f9fa",
        }
        
        bg_color = showroom_backgrounds.get(showroom_type, "#2d3748")
        
        return await self.remove_background(
            image_url=image_url,
            background_type="solid",
            background_color=bg_color,
        )

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
