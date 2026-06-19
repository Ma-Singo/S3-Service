import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.media import MediaType, MediaStatus


class MediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    media_type: MediaType
    mime_type: str
    size_bytes: int
    status: MediaStatus
    s3_key: str
    processed_s3_key: str | None
    width: int | None
    height: int | None
    page_count: int | None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    asset_id: uuid.UUID
    status: MediaStatus
    message: str
