import pytest

GOOGLE = "https://www.google.com/search?q=best+pizza&hl=en"


def test_shorten_and_redirect(client):
    r = client.post("/api/shorten", json={"url": GOOGLE})
    assert r.status_code == 200
    data = r.json()
    assert data["short_url"] == f"https://xyz.com/{data['code']}"
    assert len(data["code"]) == 6

    r2 = client.get(f"/{data['code']}")
    assert r2.status_code == 302
    assert r2.headers["location"] == GOOGLE


def test_stats_count_clicks_and_ignore_head(client):
    code = client.post("/api/shorten", json={"url": GOOGLE}).json()["code"]
    assert client.get(f"/api/links/{code}").json()["click_count"] == 0

    client.get(f"/{code}")
    client.get(f"/{code}")
    client.head(f"/{code}")  # previews/health checks are not clicks

    stats = client.get(f"/api/links/{code}").json()
    assert stats["click_count"] == 2
    assert stats["original_url"] == GOOGLE
    assert stats["short_url"] == f"https://xyz.com/{code}"


def test_stats_unknown_code_404(client):
    assert client.get("/api/links/nope12").status_code == 404


def test_codes_have_no_lookalike_characters(client):
    for _ in range(50):
        code = client.post("/api/shorten", json={"url": GOOGLE}).json()["code"]
        assert not set(code) & set("0O1lI")


def test_unknown_code_404(client):
    assert client.get("/nope12").status_code == 404


@pytest.mark.parametrize("bad", [
    "", "javascript:alert(1)", "ftp://x.com/a", "not a url", "http://localhost/x",
    "http://127.0.0.1/x", "http://10.0.0.5/x", "https://user:pw@google.com/",
    "https://" + "a" * 3000 + ".com",
])
def test_rejects_bad_urls(client, bad):
    assert client.post("/api/shorten", json={"url": bad}).status_code == 422


def test_health_and_index(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert "URL Shortener" in client.get("/").text
