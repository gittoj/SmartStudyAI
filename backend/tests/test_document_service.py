import pytest

from app.services.document_service import UploadRejected, detect_mime, validate_upload

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def test_detects_png_from_bytes() -> None:
    assert detect_mime(PNG) == "image/png"

def test_rejects_empty_file() -> None:
    with pytest.raises(UploadRejected, match="empty"):
        validate_upload("a.png", b"")

def test_rejects_extension_mismatch() -> None:
    with pytest.raises(UploadRejected, match="Use a PDF"):
        validate_upload("a.pdf", PNG)

def test_accepts_valid_png() -> None:
    assert validate_upload("a.png", PNG) == "image/png"
