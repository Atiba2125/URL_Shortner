import ipaddress
from urllib.parse import urlsplit

from .config import Settings


class InvalidURL(ValueError):
    pass


def validate_url(raw: str, settings: Settings) -> str:
    """Return a normalised URL or raise InvalidURL."""
    url = raw.strip()
    if not url:
        raise InvalidURL("URL is empty.")
    if len(url) > settings.max_url_length:
        raise InvalidURL(f"URL is longer than {settings.max_url_length} characters.")
    if any(c in url for c in ("\r", "\n", "\t", " ")):
        raise InvalidURL("URL must not contain spaces or control characters.")

    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        raise InvalidURL("URL could not be parsed.")

    if parts.scheme not in ("http", "https"):
        raise InvalidURL("Only http:// and https:// URLs are allowed.")
    if not host:
        raise InvalidURL("URL has no host.")
    if parts.username or parts.password:
        raise InvalidURL("URLs with embedded credentials are not allowed.")

    if host == "localhost" or host.endswith(".localhost"):
        raise InvalidURL("Local addresses are not allowed.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None  # not an IP literal; fine
    if ip is not None and not ip.is_global:
        raise InvalidURL("Private or local IP addresses are not allowed.")

    allowed = settings.allowed_host_set
    if allowed and host not in allowed:
        raise InvalidURL("This host is not allowed: " + ", ".join(sorted(allowed)) + " only.")

    return url
