from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .codes import generate_code
from .config import get_settings
from .db import Base, engine, get_db
from .models import Link
from .validation import InvalidURL, validate_url

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="URL Shortener", docs_url="/api/docs", openapi_url="/api/openapi.json")
Base.metadata.create_all(engine)  # swap for Alembic migrations if the schema grows


class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    original_url: str


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/api/shorten", response_model=ShortenResponse)
def shorten(body: ShortenRequest, db: Session = Depends(get_db)):
    try:
        url = validate_url(body.url, settings)
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    for _ in range(5):  # retry on the (rare) code collision
        link = Link(code=generate_code(settings.code_length), original_url=url)
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        return ShortenResponse(
            code=link.code,
            short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
            original_url=url,
        )
    raise HTTPException(status_code=503, detail="Could not allocate a short code, try again.")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)  # the page embeds its own icon


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Keep last: catch-all for short codes.
@app.api_route("/{code}", methods=["GET", "HEAD"], include_in_schema=False)
def resolve(code: str, request: Request, db: Session = Depends(get_db)):
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found.")
    if request.method == "GET":  # link-preview/health HEAD requests are not clicks
        db.execute(update(Link).where(Link.id == link.id).values(click_count=Link.click_count + 1))
        db.commit()
    # Plain redirect. The "keep custom domain in the address bar" proxy mode is
    # intentionally NOT implemented yet - see README (pending client clarification).
    return RedirectResponse(link.original_url, status_code=302)
