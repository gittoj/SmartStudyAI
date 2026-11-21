"""The only module that calls OpenAI. One call generates explanation, example, and 5 MCQs."""
from app.schemas import GeneratedWorksheet, Level, Subject

LEVEL_STYLE: dict[str, str] = {  # single source of truth for P2/P3/P4 wording
    "P2": "Short sentences, everyday words, one idea at a time.",
    "P3": "Short sentences plus one new term, defined immediately.",
    "P4": "Still simple, with one extra step in the worked example.",
}


class GenerationFailed(Exception):
    """Timeout, API error, or malformed output."""


def build_prompt(subject: Subject, level: Level, topic_hint: str | None, text: str) -> str:
    """Ground generation in the worksheet text; never copy its questions."""
    raise NotImplementedError


def validate_generated(raw_json: str) -> GeneratedWorksheet:
    """Parse with Pydantic, then enforce: expected_answer is one of the four choices."""
    parsed = GeneratedWorksheet.model_validate_json(raw_json)
    for question in parsed.questions:
        if question.expected_answer not in question.choices:
            raise GenerationFailed("answer not in choices")
    return parsed


async def generate_worksheet(subject: Subject, level: Level, topic_hint: str | None, text: str) -> GeneratedWorksheet:
    """TODO: AsyncOpenAI call, 60s timeout (settings.openai_timeout_seconds), JSON output.
    Raise GenerationFailed on any failure. Never log prompts or extracted text."""
    raise NotImplementedError
