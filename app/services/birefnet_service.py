"""
BiRefNet-based image processing service.
State-of-the-art background removal (2024).
Free, open-source, excellent for vehicles.
"""
import io
import uuid
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from functools import lru_cache

import httpx
from PIL import Image, ImageEnhance, ImageFilter
import torch
import numpy as np

from app.config import settings


class BiRefNetService:
    """
    High-quality image processing using BiRefNet.
    
    BiRefNet provides state-of-the-art background removal,
    especially excellent for vehicles and complex objects.
    """

    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._backgrounds = {
            "white": "#FFFFFF",
            "gray": "#808080",
            "dark": "#1f2937",
            "showroom": "#2d3748",
        }
        self._load_model()

    def _load_model(self):
        """Load BiRefNet model from Hugging Face."""
        try:
            from transformers import AutoModelForImageSegmentation, AutoProcessor
            
            # BiRefNet model from Hugging Face
            model_id = "ZhengPeng7/BiRefNet"
            
            self.processor = AutoProcessor.from_pretrained(
                model_id,
                trust_remote_code=True
            )
            self.model = AutoModelForImageSegmentation.from_pretrained(
                model_id,
                trust_remote_code=True
            )
            self.model.to(self.device)
            self.model.eval()
            
            print(f"✅ BiRefNet loaded on {self.device}")
            
        except ImportError:
            # Fallback to rembg if BiRefNet deps not available
            print("⚠️ BiRefNet not available, falling back to rembg")
            from rembg import remove, new_session
            self.fallback_session = new_session("u2net")
            self.model = None

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

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _birefnet_remove_bg(self, image: Image.Image) -> Image.Image:
        """Remove background using BiRefNet."""
        if self.model is None:
            # Fallback to rembg
            from rembg import remove
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="PNG")
            result = remove(img_bytes.getvalue(), session=self.fallback_session)
            return Image.open(io.BytesIO(result)).convert("RGBA")
        
        # Prepare input for BiRefNet
        original_size = image.size
        
        # Process with BiRefNet
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Get the mask
        mask = outputs.logits.squeeze().cpu().numpy()
        
        # Normalize and resize mask to original size
        mask = (mask - mask.min()) / (mask.max() - mask.min())
        mask = (mask * 255).astype(np.uint8)
        mask = Image.fromarray(mask).resize(original_size, Image.Resampling.LANCZOS)
        
        # Apply mask to create RGBA image
        image_rgba = image.convert("RGBA")
        image_rgba.putalpha(mask)
        
        return image_rgba

    async def remove_background(
        self,
        image_url: str,
        background_type: str = "transparent",
        background_color: Optional[str] = None,
        background_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Remove image background using BiRefNet (state-of-the-art).
        
        Types:
        - transparent: PNG with alpha
        - solid: Solid color background
        - custom: Custom background image
        """
        import time
        start = time.time()
        
        # Download source image
        image_bytes = await self._download_image(image_url)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Remove background using BiRefNet
        result_image = await asyncio.to_thread(
            self._birefnet_remove_bg, image
        )
        
        # Apply background based on type
        if background_type == "solid" and background_color:
            bg_color = self._hex_to_rgb(background_color)
            background = Image.new("RGBA", result_image.size, bg_color + (255,))
            background.paste(result_image, mask=result_image.split()[3])
            result_image = background.convert("RGB")
            
        elif background_type == "custom" and background_url:
            bg_bytes = await self._download_image(background_url)
            background = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
            background = background.resize(result_image.size, Image.Resampling.LANCZOS)
            background.paste(result_image, mask=result_image.split()[3])
            result_image = background.convert("RGB")
            
        elif background_type in self._backgrounds:
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
            result_image.convert("RGB").save(output, format="JPEG", quality=92)
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
            "model": "BiRefNet" if self.model else "rembg-fallback",
            "status": "completed",
        }

    async def enhance_image(
        self,
        image_url: str,
        options: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """Enhance image using PIL (free)."""
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
        """Place vehicle on showroom background."""
        showroom_backgrounds = {
            "indoor": "#1a1a2e",
            "outdoor": "#87CEEB",
            "studio": "#2d3748",
            "dark": "#0f0f0f",
            "white": "#f8f9fa",
            "gradient_dark": "#1a1a2e",
            "garage": "#3d3d3d",
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


# Singleton instance
_service_instance = None

def get_birefnet_service() -> BiRefNetService:
    """Get or create BiRefNet service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = BiRefNetService()
    return _service_instance
