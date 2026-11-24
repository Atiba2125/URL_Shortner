from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Link
from .security import require_admin
from .validation import InvalidURL, validate_url

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Every route below needs the admin login (HTTP Basic).
router = APIRouter(dependencies=[Depends(require_admin)], include_in_schema=False)


class AdminLink(BaseModel):
    id: int
    code: str
    short_url: str
    original_url: str
    click_count: int
    created_at: datetime


class AdminList(BaseModel):
    total: int
    total_clicks: int
    items: list[AdminLink]


class EditRequest(BaseModel):
    url: str


def _to_item(link: Link) -> AdminLink:
    base = get_settings().base_url.rstrip("/")
    return AdminLink(
        id=link.id,
        code=link.code,
        short_url=f"{base}/{link.code}",
        original_url=link.original_url,
        click_count=link.click_count,
        created_at=link.created_at,
    )


def _get_or_404(db: Session, code: str) -> Link:
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found.")
    return link


@router.get("/admin")
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


@router.get("/api/admin/links", response_model=AdminList)
def list_links(
    q: str = Query("", max_length=200),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Link)
    q = q.strip()
    if q:
        stmt = stmt.where(Link.code.icontains(q, autoescape=True) | Link.original_url.icontains(q, autoescape=True))
    sub = stmt.subquery()
    total = db.scalar(select(func.count()).select_from(sub)) or 0
    total_clicks = db.scalar(select(func.coalesce(func.sum(sub.c.click_count), 0))) or 0
    rows = db.scalars(stmt.order_by(Link.id.desc()).limit(limit).offset(offset)).all()
    return AdminList(total=total, total_clicks=int(total_clicks), items=[_to_item(r) for r in rows])


@router.patch("/api/admin/links/{code}", response_model=AdminLink)
def edit_link(code: str, body: EditRequest, db: Session = Depends(get_db)):
    link = _get_or_404(db, code)
    try:
        link.original_url = validate_url(body.url, get_settings())
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    return _to_item(link)


@router.delete("/api/admin/links/{code}", status_code=204)
def delete_link(code: str, db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, code))
    db.commit()
    return Response(status_code=204)
