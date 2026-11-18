"""
Upload validation for biometric images.

Every image endpoint funnels through ``read_upload_with_limits`` so that
content-type and size are enforced in one place. The check is deliberately
cheap: content-type first, then a single read whose length is bounded by the
configured maximum. A file that cannot be decoded is caught later by OpenCV.
"""

from fastapi import HTTPException, UploadFile

from app.core.config import settings


async def read_upload_with_limits(upload: UploadFile) -> bytes:
    """
    Read an uploaded image, rejecting unsupported types and oversized files.

    Raises:
        415: content type is not one of the configured image types.
        413: file exceeds ``MAX_UPLOAD_SIZE_MB``.
        400: file is empty.
    """
    content_type = (upload.content_type or "").lower()
    if content_type not in settings.allowed_image_content_types:
        allowed = ", ".join(settings.allowed_image_content_types)
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{content_type or 'unknown'}'. Allowed: {allowed}.",
        )

    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
        )
    return data
