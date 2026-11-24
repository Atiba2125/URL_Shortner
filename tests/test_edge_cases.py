import pytest

from app import cli
from app.main import limiter

GOOGLE = "https://www.google.com/search?q=best+pizza&hl=en"


def test_rate_limit_returns_429_then_recovers(client):
    limiter.limit = 3
    limiter.reset()
    codes = [client.post("/api/shorten", json={"url": GOOGLE}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    r = client.post("/api/shorten", json={"url": GOOGLE})
    assert r.headers["retry-after"] == "60"
    limiter.reset()
    assert client.post("/api/shorten", json={"url": GOOGLE}).status_code == 200


def test_same_url_gets_distinct_codes(client):
    a = client.post("/api/shorten", json={"url": GOOGLE}).json()["code"]
    b = client.post("/api/shorten", json={"url": GOOGLE}).json()["code"]
    assert a != b


def test_unicode_url_redirects(client):
    url = "https://www.google.com/search?q=café+اردو"
    code = client.post("/api/shorten", json={"url": url}).json()["code"]
    r = client.get(f"/{code}")
    assert r.status_code == 302 and r.headers["location"].startswith("https://www.google.com/search?q=caf")


def test_url_with_whitespace_around_is_trimmed(client):
    r = client.post("/api/shorten", json={"url": f"  {GOOGLE}\n"})
    assert r.status_code == 200 and r.json()["original_url"] == GOOGLE


def test_url_at_length_limit(client):
    ok = "https://example.com/" + "a" * (2048 - len("https://example.com/"))
    assert client.post("/api/shorten", json={"url": ok}).status_code == 200
    assert client.post("/api/shorten", json={"url": ok + "a"}).status_code == 422


@pytest.mark.parametrize("payload", [{}, {"url": None}, {"url": 123}, {"link": GOOGLE}, []])
def test_bad_request_bodies_are_422(client, payload):
    assert client.post("/api/shorten", json=payload).status_code == 422


def test_malformed_json_and_wrong_content_type(client):
    assert client.post("/api/shorten", content="{not json", headers={"Content-Type": "application/json"}).status_code == 422
    assert client.post("/api/shorten", content="url=x", headers={"Content-Type": "text/plain"}).status_code == 422


def test_codes_are_case_sensitive_and_reserved_paths_are_not_links(client):
    code = client.post("/api/shorten", json={"url": GOOGLE}).json()["code"]
    swapped = code.swapcase()
    if swapped != code:
        assert client.get(f"/{swapped}").status_code == 404
    assert client.get("/static/nothing.css").status_code == 404
    assert client.get("/api/docs").status_code == 200


def test_browser_gets_html_404_api_gets_json(client):
    html = client.get("/nope12", headers={"Accept": "text/html"})
    assert html.status_code == 404 and "not found" in html.text.lower() and "<html" in html.text
    js = client.get("/nope12", headers={"Accept": "application/json"})
    assert js.status_code == 404 and js.json()["detail"] == "Short link not found."
    assert client.get("/api/links/nope12", headers={"Accept": "text/html"}).json()["detail"]


def test_method_not_allowed(client):
    assert client.post("/nope12").status_code == 405
    assert client.get("/api/shorten").status_code == 405


def test_cli_create_stats_edit_delete(client, capsys):
    assert cli.main(["create", GOOGLE]) == 0
    short = capsys.readouterr().out.strip()
    assert short.startswith("https://xyz.com/")
    code = short.rsplit("/", 1)[1]

    assert cli.main(["stats", code]) == 0 and GOOGLE in capsys.readouterr().out
    assert cli.main(["edit", code, "https://example.org/x"]) == 0
    assert client.get(f"/{code}").headers["location"] == "https://example.org/x"
    assert cli.main(["list"]) == 0 and code in capsys.readouterr().out
    assert cli.main(["delete", code]) == 0
    assert client.get(f"/{code}").status_code == 404

    assert cli.main(["create", "javascript:alert(1)"]) == 1
    assert cli.main(["stats", "nope12"]) == 1
