from app.services.document_service import _summarise_ocr


def _data(rows: list[tuple[str, float, int, int, int]]) -> dict:
    return {
        "text": [r[0] for r in rows], "conf": [r[1] for r in rows],
        "block_num": [r[2] for r in rows], "par_num": [r[3] for r in rows], "line_num": [r[4] for r in rows],
    }


def test_groups_words_into_lines_and_averages_confidence() -> None:
    text, confidence = _summarise_ocr(_data([
        ("", -1, 1, 0, 0), ("Half", 90, 1, 1, 1), ("of", 80, 1, 1, 1), ("8", 70, 1, 1, 2),
    ]))
    assert text == "Half of\n8"
    assert abs(confidence - 0.8) < 1e-9


def test_no_words_means_zero_confidence() -> None:
    assert _summarise_ocr(_data([("", -1, 1, 0, 0), ("  ", 50, 1, 1, 1)])) == ("", 0.0)


import pytest

from app.services.document_service import OcrUnavailable, _summarise_google


def _word(conf: float) -> dict:
    return {"confidence": conf}


def test_google_text_and_mean_word_confidence() -> None:
    response = {"responses": [{"fullTextAnnotation": {
        "text": "Half of 8 is 4\n",
        "pages": [{"blocks": [{"paragraphs": [{"words": [_word(0.9), _word(0.7)]}]}]}],
    }}]}
    text, confidence = _summarise_google(response)
    assert text == "Half of 8 is 4" and abs(confidence - 0.8) < 1e-9


def test_google_blank_page_returns_empty() -> None:
    assert _summarise_google({"responses": [{}]}) == ("", 0.0)


def test_google_error_raises() -> None:
    with pytest.raises(OcrUnavailable):
        _summarise_google({"responses": [{"error": {"code": 3}}]})


def test_tesseract_drops_low_confidence_handwriting_noise() -> None:
    text, confidence = _summarise_ocr(_data([
        ("Half", 92, 1, 1, 1), ("of", 88, 1, 1, 1), ("xqzt", 12, 1, 1, 1),
    ]), min_word_confidence=40)
    assert text == "Half of" and abs(confidence - 0.9) < 1e-9
