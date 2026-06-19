"""
Media validation: MIME type, size, dimensions, duration
Called by the API Gateway before anything hits S3
"""

import logging
from dataclasses import dataclass
from typing import Literal
import magic

from fastapi import UploadFile, HTTPException, status

from app.core.config import settings


ALLOWED_PDF_MIMES = {
    "application/pdf",
}

ALLOWED_DOC_MIMES = {
    # Modern Word
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Legacy Word (.doc) — magic detects as this MIME
    "application/msword",
    # LibreOffice / ODF
    "application/vnd.oasis.opendocument.text",
}

ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/avif",
}


ALLOWED_MIMES = (
        ALLOWED_IMAGE_MIMES
        | ALLOWED_PDF_MIMES
        | ALLOWED_DOC_MIMES
)

@dataclass
class ValidationResult:
    media_type: Literal["image", "pdf", "document"]
    mime_type: str
    size_bytes: int
    # image
    width: int | None = None
    height: int | None = None
    # document / pdf
    page_count: int | None = None


async def validate_upload(file: UploadFile) -> ValidationResult:
    data = await file.read()
    await file.seek(0)

    mime = magic.from_buffer(data, mime=True)

    if mime not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {mime}. Allowed: {sorted(ALLOWED_MIMES)}",
        )

    if mime in ALLOWED_IMAGE_MIMES:
        return _validate_image(data, mime)

    if mime in ALLOWED_PDF_MIMES:
        return _validate_pdf(data, mime)

    return _validate_document(data, mime)


def _validate_image(data: bytes, mime: str) -> ValidationResult:
    size = len(data)
    if size > settings.max_image_size_bytes:
        _raise_too_large(size, settings.MAX_IMAGE_SIZE_MB)

    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        width, height = img.size
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Cannot read image: {exc}",
        )

    max_dim = settings.MAX_IMAGE_DIMENSION
    if width > max_dim or height > max_dim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Image too large ({width}×{height}px). Max dimension: {max_dim}px",
        )

    return ValidationResult(
        media_type="image",
        mime_type=mime,
        size_bytes=size,
        width=width,
        height=height,
    )



def _validate_pdf(data: bytes, mime: str) -> ValidationResult:
    size = len(data)
    if size > settings.max_pdf_size_bytes:
        _raise_too_large(size, settings.MAX_IMAGE_SIZE_MB)

    page_count = _count_pdf_pages(data)
    if page_count is not None and page_count > settings.MAX_PDF_PAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"PDF has too many pages ({page_count}). "
                f"Max: {settings.MAX_PDF_PAGES}"
            ),
        )

    return ValidationResult(
        media_type="pdf",
        mime_type=mime,
        size_bytes=size,
        page_count=page_count,
    )


def _validate_document(data: bytes, mime: str) -> ValidationResult:
    size = len(data)
    if size > settings.max_doc_size_bytes:
        _raise_too_large(size, settings.MAX_DOC_SIZE_MB)

    page_count = None

    if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        page_count = _count_docx_pages(data)
        if page_count is not None and page_count > settings.MAX_DOC_PAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Document has too many pages ({page_count}). "
                    f"Max: {settings.MAX_DOC_PAGES}"
                ),
            )

    return ValidationResult(
        media_type="document",
        mime_type=mime,
        size_bytes=size,
        page_count=page_count,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _raise_too_large(size: int, limit_mb: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=(
            f"File too large ({size / 1024 / 1024:.1f}MB). "
            f"Max: {limit_mb}MB"
        ),
    )


def _count_pdf_pages(data: bytes) -> int | None:
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(data))
        return len(reader.pages)
    except ImportError:
        return None
    except Exception:
        return None


def _count_docx_pages(data: bytes) -> int | None:
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(data))
        props = doc.core_properties
        pages = getattr(props, "pages", None)
        return int(pages) if pages is not None else None
    except ImportError:
        return None
    except Exception:
        return None
