"""File-type detection, upload validation, PDF text extraction, and OCR."""
from dataclasses import dataclass

import fitz  # PyMuPDF

from app.core.config import settings

ALLOWED = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}
OCR_MIN_CONFIDENCE = 0.6
MIN_TOTAL_CHARS = 20


class UploadRejected(Exception):
    """Carries the exact parent-facing message from the spec's validation table."""


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    confidence: float | None  # None for PDF text layer


def detect_mime(data: bytes) -> str | None:
    """Detect type from bytes, not from the file extension."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_upload(file_name: str, data: bytes) -> str:
    """Return the detected mime type or raise UploadRejected. Runs before anything is stored."""
    if len(data) == 0:
        raise UploadRejected("This file is empty. Choose a worksheet photo or PDF.")
    if len(data) > settings.max_upload_bytes:
        raise UploadRejected("This file is larger than 10 MB. Take a closer photo or export a smaller PDF.")
    mime = detect_mime(data)
    extension = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if mime is None or extension not in ALLOWED[mime]:
        raise UploadRejected("Use a PDF, JPG, PNG, or WEBP worksheet.")
    if mime == "application/pdf":
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                if doc.page_count > settings.max_pdf_pages:
                    raise UploadRejected("This PDF has more than 10 pages. Upload one worksheet at a time.")
        except UploadRejected:
            raise
        except Exception as error:  # corrupt PDF
            raise UploadRejected("Use a PDF, JPG, PNG, or WEBP worksheet.") from error
    return mime


async def extract_pages(data: bytes, mime: str) -> list[ExtractedPage]:
    """PyMuPDF for text-layer PDF pages; OCR for photos and image-only PDF pages.

    Run blocking PyMuPDF calls via asyncio.to_thread. Do not keep page images after reading.
    """
    raise NotImplementedError


async def run_ocr(image_bytes: bytes) -> tuple[str, float]:
    """TODO: call the OCR service using OCR_API_KEY from settings. Returns (text, confidence 0-1)."""
    raise NotImplementedError


def is_readable(pages: list[ExtractedPage]) -> bool:
    """Readable pages: text layer, or OCR confidence >= 0.6. Combined text must be >= 20 chars."""
    good = [p for p in pages if p.confidence is None or p.confidence >= OCR_MIN_CONFIDENCE]
    return bool(good) and sum(len(p.text.strip()) for p in good) >= MIN_TOTAL_CHARS
