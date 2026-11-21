from app.services.analytics_service import calculate_mastery


def test_not_started() -> None:
    assert calculate_mastery([]) == "not_started"

def test_needs_practice_below_half() -> None:
    assert calculate_mastery([True, False, False, False]) == "needs_practice"

def test_developing_between_50_and_79() -> None:
    assert calculate_mastery([True, True, True, False, False]) == "developing"

def test_high_score_with_few_attempts_is_developing() -> None:
    assert calculate_mastery([True, True, True, True]) == "developing"

def test_confident_needs_five_attempts() -> None:
    assert calculate_mastery([True] * 5) == "confident"

def test_only_latest_ten_count() -> None:
    assert calculate_mastery([True] * 10 + [False] * 20) == "confident"
