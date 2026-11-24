from app.config import get_settings

GOOGLE = "https://www.google.com/search?q=best+pizza&hl=en"


def make(client, url=GOOGLE):
    return client.post("/api/shorten", json={"url": url}).json()["code"]


def test_admin_requires_login(client):
    assert client.get("/admin").status_code == 401
    assert client.get("/api/admin/links").status_code == 401
    r = client.get("/api/admin/links", auth=("admin", "wrong"))
    assert r.status_code == 401
    assert "Basic" in r.headers["www-authenticate"]
    assert client.get("/admin", auth=("wrong", "test-admin-pass")).status_code == 401


def test_admin_page_loads_with_login(client, admin):
    r = client.get("/admin", auth=admin)
    assert r.status_code == 200 and "Admin" in r.text


def test_admin_disabled_without_password(client, admin, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "")
    assert client.get("/api/admin/links", auth=admin).status_code == 503


def test_admin_list_search_pagination(client, admin):
    for i in range(5):
        make(client, f"https://example.com/page{i}")
    code = make(client, "https://www.google.com/search?q=find+me")
    client.get(f"/{code}")

    data = client.get("/api/admin/links", auth=admin).json()
    assert data["total"] == 6 and data["total_clicks"] == 1
    assert data["items"][0]["code"] == code  # newest first

    page = client.get("/api/admin/links?limit=2&offset=4", auth=admin).json()
    assert len(page["items"]) == 2 and page["total"] == 6

    found = client.get("/api/admin/links?q=find%2Bme", auth=admin).json()  # %2B = a literal "+"
    assert found["total"] == 1 and found["items"][0]["code"] == code

    assert client.get("/api/admin/links?q=zzzz-nothing", auth=admin).json()["total"] == 0
    assert client.get("/api/admin/links?q=%25", auth=admin).json()["total"] == 0  # % is literal, not a wildcard
    assert client.get("/api/admin/links?limit=0", auth=admin).status_code == 422


def test_admin_edit_changes_redirect(client, admin):
    code = make(client)
    r = client.patch(f"/api/admin/links/{code}", json={"url": "https://example.org/new"}, auth=admin)
    assert r.status_code == 200 and r.json()["original_url"] == "https://example.org/new"
    assert client.get(f"/{code}").headers["location"] == "https://example.org/new"


def test_admin_edit_rejects_bad_url_and_unknown_code(client, admin):
    code = make(client)
    assert client.patch(f"/api/admin/links/{code}", json={"url": "javascript:alert(1)"}, auth=admin).status_code == 422
    assert client.patch("/api/admin/links/nope12", json={"url": "https://a.com"}, auth=admin).status_code == 404
    assert client.get(f"/{code}").headers["location"] == GOOGLE  # unchanged


def test_admin_delete(client, admin):
    code = make(client)
    assert client.delete(f"/api/admin/links/{code}").status_code == 401
    assert client.delete(f"/api/admin/links/{code}", auth=admin).status_code == 204
    assert client.get(f"/{code}").status_code == 404
    assert client.delete(f"/api/admin/links/{code}", auth=admin).status_code == 404
