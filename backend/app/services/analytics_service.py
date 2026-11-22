from sqlalchemy import exists, select

from app.models import Attempt, QuestionReport, TopicProgress, Worksheet
from app.schemas import Mastery

WINDOW = 10
MASTERY_ORDER: list[Mastery] = ["needs_practice", "developing", "confident", "not_started"]


def calculate_mastery(latest_results: list[bool]) -> Mastery:
    """Mastery from the latest 10 attempts (pass newest-first, or any <=10 list).

    not_started: none; needs_practice: <50%; confident: >=80% with >=5 attempts;
    developing: everything else (50-79%, or >=80% with fewer than 5 attempts).
    """
    window = latest_results[:WINDOW]
    if not window:
        return "not_started"
    percent = sum(window) / len(window) * 100
    if percent < 50:
        return "needs_practice"
    if percent >= 80 and len(window) >= 5:
        return "confident"
    return "developing"


async def refresh_topic_progress(db, child_id, subject: str, level: str, topic: str) -> TopicProgress:
    """Recompute one topic's progress from this child's attempts. The caller commits.

    Mastery uses the latest 10 attempts. The attempted/correct counts cover all attempts
    on the topic, across every worksheet, so a new worksheet never resets progress.
    """
    rows = (await db.execute(
        select(Attempt.is_correct, Attempt.submitted_at)
        .join(Worksheet, Worksheet.id == Attempt.worksheet_id)
        .where(Attempt.child_id == child_id, Worksheet.subject == subject, Worksheet.topic == topic)
        # A question the child flagged stays out of progress until the parent says it is fine.
        .where(~exists().where(
            QuestionReport.child_id == Attempt.child_id, QuestionReport.question_id == Attempt.question_id,
            QuestionReport.status != "dismissed"))
        .order_by(Attempt.submitted_at.desc(), Attempt.id.desc())
    )).all()
    results = [row.is_correct for row in rows]

    progress = (await db.execute(select(TopicProgress).where(
        TopicProgress.child_id == child_id, TopicProgress.subject == subject, TopicProgress.topic == topic
    ))).scalar_one_or_none()
    if progress is None:
        progress = TopicProgress(child_id=child_id, subject=subject, level=level, topic=topic)
        db.add(progress)
    progress.questions_attempted = len(results)
    progress.questions_correct = sum(results)
    progress.last_practised_at = rows[0].submitted_at if rows else None
    progress.mastery = calculate_mastery(results)
    return progress
