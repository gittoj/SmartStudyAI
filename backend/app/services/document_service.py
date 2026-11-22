"""File-type detection, upload validation, PDF text extraction, and OCR."""
import asyncio
import io
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass

import pymupdf

from app.core.config import settings

logger = logging.getLogger(__name__)

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
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                if doc.page_count > settings.max_pdf_pages:
                    raise UploadRejected("This PDF has more than 10 pages. Upload one worksheet at a time.")
        except UploadRejected:
            raise
        except Exception as error:  # corrupt PDF
            raise UploadRejected("Use a PDF, JPG, PNG, or WEBP worksheet.") from error
    return mime


RENDER_DPI = 150


class OcrUnavailable(Exception):
    """OCR provider missing, misconfigured, or failing."""


def _read_pdf_text_layer(data: bytes) -> list[str]:
    """Blocking PyMuPDF call: text per page ('' when the page has no text layer)."""
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        return [page.get_text().strip() for page in doc]


def _render_page_png(data: bytes, index: int) -> bytes:
    """Blocking: render one page. The caller drops the bytes right after OCR."""
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        return doc[index].get_pixmap(dpi=RENDER_DPI).tobytes("png")


async def extract_pages(data: bytes, mime: str) -> list[ExtractedPage]:
    """PyMuPDF for text-layer PDF pages; OCR for photos and image-only PDF pages.
    Page images exist only inside this function and are never persisted."""
    if mime != "application/pdf":
        text, confidence = await run_ocr(data)
        return [ExtractedPage(1, text, confidence)]
    layers = await asyncio.to_thread(_read_pdf_text_layer, data)
    pages: list[ExtractedPage] = []
    for index, text in enumerate(layers):
        if text:
            pages.append(ExtractedPage(index + 1, text, None))
            continue
        image = await asyncio.to_thread(_render_page_png, data, index)
        ocr_text, confidence = await run_ocr(image)
        del image
        pages.append(ExtractedPage(index + 1, ocr_text, confidence))
    return pages


MAX_OCR_SIDE_PIXELS = 3000


def _summarise_ocr(data: dict, min_word_confidence: float = 0.0) -> tuple[str, float]:
    """Turn Tesseract word data into (text in reading order, mean word confidence 0-1).
    Words below min_word_confidence (0-100) are dropped: on a worksheet with handwritten answers
    they are mostly handwriting noise, and the printed questions are what matter."""
    lines: dict[tuple[int, int, int], list[str]] = {}
    confidences: list[float] = []
    for text, conf, block, paragraph, line in zip(
        data["text"], data["conf"], data["block_num"], data["par_num"], data["line_num"]
    ):
        word = str(text).strip()
        try:
            score = float(conf)
        except (TypeError, ValueError):
            continue
        if not word or score < 0 or score < min_word_confidence:  # -1 marks layout rows
            continue
        lines.setdefault((block, paragraph, line), []).append(word)
        confidences.append(score)
    if not confidences:
        return "", 0.0
    return "\n".join(" ".join(words) for words in lines.values()), sum(confidences) / len(confidences) / 100


def _find_tesseract() -> str | None:
    """TESSERACT_CMD if set, else PATH, else the usual Windows install folders."""
    configured = settings.tesseract_cmd.strip().strip('"').strip("'")
    if configured:
        return configured
    found = shutil.which("tesseract")
    if found:
        return found
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
    ]
    return next((c for c in candidates if Path(c).exists()), None)


def _ocr_sync(image_bytes: bytes) -> tuple[str, float]:
    """Blocking Tesseract call, run in a worker thread. Runs locally: no data leaves the server."""
    import pytesseract
    from PIL import Image, ImageOps

    executable = _find_tesseract()
    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable
    with Image.open(io.BytesIO(image_bytes)) as original:
        image = ImageOps.grayscale(ImageOps.exif_transpose(original))  # fix phone-photo rotation
    image.thumbnail((MAX_OCR_SIDE_PIXELS, MAX_OCR_SIDE_PIXELS))
    data = pytesseract.image_to_data(image, lang="eng", output_type=pytesseract.Output.DICT, timeout=30)
    return _summarise_ocr(data, settings.tesseract_min_word_confidence)


def _prepare_jpeg(image_bytes: bytes) -> bytes:
    """Upright, shrink and re-encode as JPEG so the request stays well under provider size limits."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(image_bytes)) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    image.thumbnail((MAX_OCR_SIDE_PIXELS, MAX_OCR_SIDE_PIXELS))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _summarise_google(response: dict) -> tuple[str, float]:
    """Google Vision DOCUMENT_TEXT_DETECTION response -> (text, mean word confidence 0-1)."""
    result = (response.get("responses") or [{}])[0]
    if "error" in result:
        raise OcrUnavailable("vision_error")
    annotation = result.get("fullTextAnnotation")
    if not annotation:
        return "", 0.0
    confidences = [
        word["confidence"]
        for page in annotation.get("pages", []) for block in page.get("blocks", [])
        for paragraph in block.get("paragraphs", []) for word in paragraph.get("words", [])
        if "confidence" in word
    ]
    if not confidences:
        pages = annotation.get("pages") or [{}]
        return annotation.get("text", "").strip(), float(pages[0].get("confidence", 0.0))
    return annotation.get("text", "").strip(), sum(confidences) / len(confidences)


async def _google_vision_ocr(image_bytes: bytes) -> tuple[str, float]:
    """Google Cloud Vision DOCUMENT_TEXT_DETECTION: reads printed and handwritten text."""
    import base64

    import httpx

    if not settings.google_vision_api_key:
        raise OcrUnavailable("missing_api_key")
    jpeg = await asyncio.to_thread(_prepare_jpeg, image_bytes)
    body = {"requests": [{
        "image": {"content": base64.b64encode(jpeg).decode("ascii")},
        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
        "imageContext": {"languageHints": ["en"]},
    }]}
    async with httpx.AsyncClient(timeout=30) as client:
        # Key goes in a header, not the URL, so it cannot leak through logged URLs.
        response = await client.post(
            "https://vision.googleapis.com/v1/images:annotate",
            headers={"X-Goog-Api-Key": settings.google_vision_api_key}, json=body)
    if response.status_code != 200:
        raise OcrUnavailable(f"http_{response.status_code}")
    return _summarise_google(response.json())


_usage_lock = asyncio.Lock()


def _reserve_unit_sync() -> bool:
    """Count one Google Vision unit for this month; False once the cap is reached.
    Single-process file counter. With several workers, move it to the database."""
    path = Path(settings.storage_dir) / "ocr_usage.json"
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    try:
        used = int(json.loads(path.read_text()).get(month, 0))
    except (OSError, ValueError, AttributeError):
        used = 0
    if used >= settings.google_vision_monthly_limit:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({month: used + 1}))
    return True


async def _reserve_google_unit() -> bool:
    async with _usage_lock:
        return await asyncio.to_thread(_reserve_unit_sync)


async def run_ocr(image_bytes: bytes) -> tuple[str, float]:
    """Return (text, confidence 0-1). With OCR_PROVIDER=google_vision, Google is used until the
    monthly cap (default 900, under the 1,000 free units) is reached; then local Tesseract is used,
    so the bill stays at zero. Any failure raises OcrUnavailable.
    Never log image bytes, text, or the API key."""
    try:
        if settings.ocr_provider == "google_vision":
            if not settings.google_vision_api_key:
                raise OcrUnavailable("missing_api_key")
            if await _reserve_google_unit():
                return await _google_vision_ocr(image_bytes)
            logger.warning("ocr provider=google_vision monthly cap reached, using tesseract")
        return await asyncio.to_thread(_ocr_sync, image_bytes)
    except OcrUnavailable:
        raise
    except Exception as error:
        raise OcrUnavailable(type(error).__name__) from error


def is_readable(pages: list[ExtractedPage]) -> bool:
    """Readable pages: text layer, or OCR confidence >= 0.6. Combined text must be >= 20 chars."""
    return len(readable_text(pages).strip()) >= MIN_TOTAL_CHARS


def readable_text(pages: list[ExtractedPage]) -> str:
    good = [p for p in pages if p.confidence is None or p.confidence >= OCR_MIN_CONFIDENCE]
    return "\n\n".join(p.text.strip() for p in good if p.text.strip())
