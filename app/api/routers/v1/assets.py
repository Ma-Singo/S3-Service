import uuid
from fastapi import Depends, HTTPException, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.media import Media, MediaStatus
from app.services.media_service import storage
from app.schemas.media import MediaResponse

router = APIRouter(prefix="/assets", tags=["assets"])


async def _get_assets_or_404(
    asset_id: uuid.UUID,
    db: AsyncSession,
) -> Media:
    asset = await db.get(Media, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return asset


@router.get("/{asset_id}", response_model=MediaResponse)
async def get_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_assets_or_404(asset_id, db)


@router.get("/{asset_id}/url")
async def get_download_url(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    asset = await _get_assets_or_404(asset_id, db)
    if asset.status != MediaStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset not ready yet. Current status: {asset.status}",
        )
    if asset.processed_s3_key:
        url = storage.presigned_url(asset.processed_s3_key)
    else:
        url = storage.presigned_url(asset.s3_key)
    return {
        "asset_id": str(asset_id),
        "url": url,
        "expires_in": 3600,
    }


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    asset = await _get_assets_or_404(asset_id, db)
    await db.delete(asset)
    await db.commit()
