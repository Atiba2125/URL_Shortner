import os

# Must be set before the app is imported. Real env vars beat .env, so tests never touch PostgreSQL.
os.environ["DATABASE_URL"] = "sqlite:///./test_shortener.db"
os.environ["BASE_URL"] = "https://xyz.com"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-admin-pass"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app, limiter


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limiter.reset()
    limiter.limit = 1000
    return TestClient(app, follow_redirects=False)


@pytest.fixture()
def admin():
    return ("admin", "test-admin-pass")
