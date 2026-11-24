"""Copy links from a local SQLite file into the database in DATABASE_URL (e.g. PostgreSQL).

Usage (from the project root, with the venv active):
    python -m scripts.migrate_sqlite_to_db shortener.db

Links whose code already exists in the target database are skipped, so it is safe to run twice.
"""
import sqlite3
import sys

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Link


def main(path: str) -> None:
    if engine.dialect.name == "sqlite":
        sys.exit("DATABASE_URL still points to SQLite. Set it to PostgreSQL in .env first.")

    Base.metadata.create_all(engine)
    src = sqlite3.connect(path)
    src.row_factory = sqlite3.Row
    rows = src.execute("SELECT code, original_url, click_count, created_at FROM links ORDER BY id").fetchall()

    copied = skipped = 0
    with SessionLocal() as db:
        for r in rows:
            if db.scalar(select(Link.id).where(Link.code == r["code"])):
                skipped += 1
                continue
            link = Link(code=r["code"], original_url=r["original_url"], click_count=r["click_count"])
            if r["created_at"]:
                from datetime import datetime, timezone
                link.created_at = datetime.fromisoformat(r["created_at"]).replace(tzinfo=timezone.utc)
            db.add(link)
            copied += 1
        db.commit()
    print(f"Copied {copied} link(s), skipped {skipped} already present.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m scripts.migrate_sqlite_to_db <sqlite-file>")
    main(sys.argv[1])
