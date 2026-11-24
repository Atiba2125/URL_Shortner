from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .codes import generate_code
from .config import get_settings
from .models import Link


class CodeAllocationError(RuntimeError):
    pass


def create_link(db: Session, url: str) -> Link:
    """Store an already-validated URL under a fresh short code (retries on the rare collision)."""
    length = get_settings().code_length
    for _ in range(5):
        link = Link(code=generate_code(length), original_url=url)
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        return link
    raise CodeAllocationError("Could not allocate a short code.")
