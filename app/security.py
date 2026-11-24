import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import get_settings

_basic = HTTPBasic(auto_error=False)


def require_admin(credentials: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    settings = get_settings()
    if not settings.admin_password:
        raise HTTPException(status_code=503, detail="Admin panel is disabled: set ADMIN_PASSWORD in .env.")
    ok = credentials is not None and (
        secrets.compare_digest(credentials.username.encode(), settings.admin_username.encode())
        & secrets.compare_digest(credentials.password.encode(), settings.admin_password.encode())
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Login required.",
            headers={"WWW-Authenticate": 'Basic realm="URL Shortener admin"'},
        )
