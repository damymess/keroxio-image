from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional

from app.config import settings
from app.services.storage import StorageService
from app.services.rembg_service import RembgService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate JWT token and return user info."""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "id": user_id,
            "email": payload.get("email"),
            "garage_name": payload.get("garage_name"),
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return StorageService()


# Singleton instance for rembg (model loaded once)
_rembg_service: RembgService = None

def get_image_processing_service() -> RembgService:
    """Get image processing service instance (rembg - free, self-hosted)."""
    global _rembg_service
    if _rembg_service is None:
        _rembg_service = RembgService()
    return _rembg_service

# Alias for backward compatibility
def get_nano_banana_service() -> RembgService:
    """Deprecated: Use get_image_processing_service instead."""
    return get_image_processing_service()
