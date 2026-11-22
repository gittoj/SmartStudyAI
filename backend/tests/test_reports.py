from tests.test_practice_dashboard import (  # noqa: F401  (env is a fixture)
    PASSWORD, child_login, create_child, env, register_and_login, seed_worksheet,
)


async def answer(client, question_id: str, choice: str) -> None:
    assert (await client.post(f"/api/practice/questions/{question_id}/answer", json={"answer": choice})).status_code == 200


async def report(client, question_id: str, reason: str = "answer_looks_wrong"):
    return await client.post(f"/api/practice/questions/{question_id}/report", json={"reason": reason})


async def parent_again(client, email: str = "p@example.com") -> None:
    assert (await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})).status_code == 200


async def topic(client, child_id: str) -> tuple[dict, dict]:
    body = (await client.get(f"/api/dashboard/{child_id}")).json()
    return body, next(t for t in body["topics"] if t["topic"] == "fractions")


async def setup(factory, client):
    await register_and_login(client)
    child_id = await create_child(client)
    _, questions = await seed_worksheet(factory, child_id)
    await child_login(client, child_id)
    return child_id, questions


async def test_report_needs_an_answer_first_and_is_idempotent(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        child_id, questions = await setup(factory, client)
        assert (await report(client, questions[0])).status_code == 409
        await answer(client, questions[0], "2")
        assert (await report(client, questions[0])).status_code == 204
        assert (await report(client, questions[0], "dont_understand")).status_code == 204
        await parent_again(client)
        body, _ = await topic(client, child_id)
        assert len(body["reportedQuestions"]) == 1


async def test_reason_must_be_one_of_the_fixed_choices(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        _, questions = await setup(factory, client)
        await answer(client, questions[0], "2")
        assert (await report(client, questions[0], "free text here")).status_code == 422


async def test_reported_question_leaves_progress_until_parent_dismisses(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        child_id, questions = await setup(factory, client)
        await answer(client, questions[0], "1")  # wrong
        await answer(client, questions[1], "2")  # right
        assert (await report(client, questions[0])).status_code == 204
        await parent_again(client)
        body, progress = await topic(client, child_id)
        assert progress["questionsAttempted"] == 1 and progress["questionsCorrect"] == 1
        reported = body["reportedQuestions"][0]
        assert reported["prompt"] == "Q1?" and reported["correctChoice"] == "2" and reported["reason"] == "answer_looks_wrong"

        url = f"/api/dashboard/{child_id}/reports/{reported['id']}"
        assert (await client.post(url, json={"resolution": "dismissed"})).status_code == 204
        body, progress = await topic(client, child_id)
        assert progress["questionsAttempted"] == 2 and body["reportedQuestions"] == []


async def test_confirmed_report_stays_out_of_progress(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        child_id, questions = await setup(factory, client)
        await answer(client, questions[0], "1")
        await report(client, questions[0])
        await parent_again(client)
        body, _ = await topic(client, child_id)
        url = f"/api/dashboard/{child_id}/reports/{body['reportedQuestions'][0]['id']}"
        assert (await client.post(url, json={"resolution": "confirmed"})).status_code == 204
        body, progress = await topic(client, child_id)
        assert progress["questionsAttempted"] == 0 and body["reportedQuestions"] == []


async def test_another_parent_cannot_see_or_resolve_a_report(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        child_id, questions = await setup(factory, client)
        await answer(client, questions[0], "1")
        await report(client, questions[0])
        await parent_again(client)
        report_id = (await topic(client, child_id))[0]["reportedQuestions"][0]["id"]
    async with make_client() as stranger:
        await register_and_login(stranger, "other@example.com")
        url = f"/api/dashboard/{child_id}/reports/{report_id}"
        assert (await stranger.post(url, json={"resolution": "dismissed"})).status_code == 404
        assert (await stranger.get(f"/api/dashboard/{child_id}")).status_code == 404


async def test_a_child_cannot_report_another_childs_question(env) -> None:
    factory, make_client = env
    async with make_client() as client:
        await register_and_login(client)
        first = await create_child(client, "alex")
        second = await create_child(client, "bella")
        _, questions = await seed_worksheet(factory, first)
        await child_login(client, second)
        assert (await report(client, questions[0])).status_code == 404
