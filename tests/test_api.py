import os

os.environ["DATABASE_URL"] = "sqlite:///./test_shortener.db"
os.environ["BASE_URL"] = "https://xyz.com"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app, follow_redirects=False)


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
