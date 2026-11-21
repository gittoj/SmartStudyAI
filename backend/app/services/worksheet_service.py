"""Upload -> read -> generate pipeline. Status flow: uploaded -> processing -> ready|needs_review|failed."""
import uuid

NEEDS_REVIEW_UNREADABLE = "We could not read this clearly. Upload a brighter, flatter photo."
FAILED_MESSAGE = "We could not prepare this worksheet. Try again."
MAX_IN_PROGRESS_PER_CHILD = 20
MAX_CONCURRENT_PER_PARENT = 2


def normalise_topic(topic: str) -> str:
    """One consistent topic name per subject + concept (lowercase, collapsed whitespace)."""
    return " ".join(topic.lower().split())


async def create_worksheet(db, parent, child, subject: str, topic_hint: str | None, file_name: str, data: bytes) -> uuid.UUID:
    """TODO: validate_upload -> in-progress checks -> store privately (key only) -> insert row
    (status=uploaded) -> schedule process_worksheet as a background task."""
    raise NotImplementedError


async def process_worksheet(worksheet_id: uuid.UUID) -> None:
    """TODO: set processing -> extract_pages (reuse stored text on retry) -> is_readable else needs_review
    -> subject mismatch check -> generate_worksheet (60s) -> validate -> save questions + AnswerKey
    -> ready. On failure: failed (keep file 7 days). Delete page images after a successful read.
    Log only worksheet id, status, error code."""
    raise NotImplementedError


async def retry_worksheet(db, worksheet_id: uuid.UUID) -> None:
    """Allow exactly one retry from the same file; reuse extracted text."""
    raise NotImplementedError
