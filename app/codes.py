import secrets
import string

# No look-alike characters (0/O, 1/l/I) so codes are easy to read and type.
ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")

# Paths that must never be issued as short codes.
RESERVED = {"api", "static", "health", "docs", "redoc", "openapi", "favicon", "robots", "admin"}


def generate_code(length: int) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if code.lower() not in RESERVED:
            return code
