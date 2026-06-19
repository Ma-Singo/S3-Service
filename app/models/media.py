import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    DateTime,
    Enum,
    JSON,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MediaType(str, enum.Enum):
    PDF     = "pdf"
    DOCUMENT = "document"
    IMAGE = "image"


class MediaStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Media(Base):
    __tablename__ = "media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_filename: Mapped[str] = mapped_column(String(512))
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType,  name="mediatype", values_callable=lambda e: [m.value for m in e]))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus,  name="mediastatus", values_callable=lambda e: [m.value for m in e]), default=MediaStatus.PENDING, index=True
    )
    # Image
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Document/ pdf
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    s3_key: Mapped[str] = mapped_column(String(1024))
    processed_s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)





