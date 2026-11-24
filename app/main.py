from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .admin import router as admin_router
from .config import get_settings
from .db import Base, engine, get_db
from .models import Link
from .ratelimit import RateLimiter
from .service import CodeAllocationError, create_link
from .validation import InvalidURL, validate_url

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
limiter = RateLimiter(settings.rate_limit_per_minute)

app = FastAPI(title="URL Shortener", docs_url="/api/docs", openapi_url="/api/openapi.json")
Base.metadata.create_all(engine)  # swap for Alembic migrations if the schema grows


@app.exception_handler(StarletteHTTPException)
async def friendly_404(request: Request, exc: StarletteHTTPException):
    """Browsers get a readable 404 page; API clients keep the JSON error."""
    wants_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code == 404 and wants_html and not request.url.path.startswith("/api"):
        return FileResponse(STATIC_DIR / "404.html", status_code=404)
    return await http_exception_handler(request, exc)


class ShortenRequest(BaseModel):
    url: str


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    original_url: str


class StatsResponse(BaseModel):
    code: str
    short_url: str
    original_url: str
    click_count: int
    created_at: datetime


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/api/shorten", response_model=ShortenResponse)
def shorten(body: ShortenRequest, request: Request, db: Session = Depends(get_db)):
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(
            status_code=429,
            detail="Too many links created. Please wait a minute and try again.",
            headers={"Retry-After": "60"},
        )
    try:
        url = validate_url(body.url, settings)
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        link = create_link(db, url)
    except CodeAllocationError:
        raise HTTPException(status_code=503, detail="Could not allocate a short code, try again.")
    return ShortenResponse(
        code=link.code,
        short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
        original_url=url,
    )


@app.get("/api/links/{code}", response_model=StatsResponse)
def link_stats(code: str, db: Session = Depends(get_db)):
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found.")
    return StatsResponse(
        code=link.code,
        short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
        original_url=link.original_url,
        click_count=link.click_count,
        created_at=link.created_at,
    )


# Admin panel (login required). Must be registered before the /{code} catch-all.
app.include_router(admin_router)


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
    # Plain redirect to the original page. Serving that page under this domain
    # (a masking proxy) is intentionally not implemented - see README.
    return RedirectResponse(link.original_url, status_code=302)
