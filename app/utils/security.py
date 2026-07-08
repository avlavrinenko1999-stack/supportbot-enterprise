import hashlib
import secrets


def generate_invite_token() -> str:
    return "INV_" + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
