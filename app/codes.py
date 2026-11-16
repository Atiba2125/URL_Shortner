import secrets
import string

ALPHABET = string.ascii_letters + string.digits

# Paths that must never be issued as short codes.
RESERVED = {"api", "static", "health", "docs", "redoc", "openapi", "favicon", "robots", "admin"}


def generate_code(length: int) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if code.lower() not in RESERVED:
            return code
