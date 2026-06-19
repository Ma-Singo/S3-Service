import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.media import Media, MediaStatus, MediaType
from app.schemas.media import UploadResponse
from app.services.media_service import storage
from app.services.validation import validate_upload
from app.core.logging import logger


router = APIRouter(prefix="/upload", tags=["upload"])



@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_media(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    validation = await validate_upload(file)
    data = await file.read()

    try:
        raw_key = storage.upload_raw(
            data=data,
            filename=file.filename or "upload",
            mime_type=validation.mime_type,
        )
    except Exception as e:
        logger.error(f"S3 upload failed for asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage service unavailable. please try again later",
        )

    asset_id = uuid.uuid4()
    asset = Media(
        id=asset_id,
        original_filename=file.filename or "upload",
        media_type=MediaType(validation.media_type),
        mime_type=validation.mime_type,
        size_bytes=validation.size_bytes,
        s3_key=raw_key,
        width=validation.width,
        height=validation.height,
        page_count=validation.page_count,
        status=MediaStatus.PENDING,
    )
    db.add(asset)
    db.flush()

    await db.commit()
    await db.refresh(asset)

    logger.info(
        f"Upload accepted: asset={asset_id}  type={validation.media_type} size={validation.size_bytes}"
    )
    return UploadResponse(
        asset_id=asset_id,
        status=MediaStatus.PENDING,
        message="Upload accepted. Processing started.",
    )

