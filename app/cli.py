"""Command-line tool for managing links on the server (no web login needed).

    python -m app.cli create "https://www.google.com/search?q=pizza"
    python -m app.cli list [--limit 20]
    python -m app.cli stats <code>
    python -m app.cli edit <code> "https://new-url"
    python -m app.cli delete <code>
"""
import argparse
import sys

from sqlalchemy import select

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import Link
from .service import CodeAllocationError, create_link
from .validation import InvalidURL, validate_url


def _short(code: str) -> str:
    return f"{get_settings().base_url.rstrip('/')}/{code}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Manage short links.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", help="shorten a URL"); c.add_argument("url")
    l = sub.add_parser("list", help="list latest links"); l.add_argument("--limit", type=int, default=20)
    s = sub.add_parser("stats", help="show one link"); s.add_argument("code")
    e = sub.add_parser("edit", help="change a link's target URL"); e.add_argument("code"); e.add_argument("url")
    d = sub.add_parser("delete", help="delete a link"); d.add_argument("code")
    args = parser.parse_args(argv)

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if args.cmd == "create":
            try:
                link = create_link(db, validate_url(args.url, get_settings()))
            except (InvalidURL, CodeAllocationError) as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 1
            print(_short(link.code))
            return 0

        if args.cmd == "list":
            rows = db.scalars(select(Link).order_by(Link.id.desc()).limit(max(args.limit, 1))).all()
            for r in rows:
                print(f"{r.code}\t{r.click_count:>5} clicks\t{r.original_url}")
            print(f"({len(rows)} shown)")
            return 0

        link = db.scalar(select(Link).where(Link.code == args.code))
        if link is None:
            print("Error: short link not found.", file=sys.stderr)
            return 1

        if args.cmd == "stats":
            print(f"short:   {_short(link.code)}\ntarget:  {link.original_url}\nclicks:  {link.click_count}\ncreated: {link.created_at}")
        elif args.cmd == "edit":
            try:
                link.original_url = validate_url(args.url, get_settings())
            except InvalidURL as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 1
            db.commit()
            print("Updated.")
        elif args.cmd == "delete":
            db.delete(link)
            db.commit()
            print("Deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
