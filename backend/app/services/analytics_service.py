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


async def refresh_topic_progress(db, child_id, subject, level, topic) -> None:
    """TODO: load latest 10 attempts for (child, subject, topic) via worksheets join,
    recompute mastery/attempted/correct/last_practised_at, upsert TopicProgress."""
    raise NotImplementedError
