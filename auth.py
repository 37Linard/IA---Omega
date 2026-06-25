import jwt
import logging
from datetime import datetime, timedelta, timezone
from config import AUTH_PASSWORD, JWT_SECRET, JWT_EXPIRE_HOURS

log = logging.getLogger(__name__)


def create_token(password: str) -> str | None:
    if not AUTH_PASSWORD:
        return "no-auth"
    if password != AUTH_PASSWORD:
        return None
    payload = {"exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> bool:
    if not AUTH_PASSWORD:
        return True
    if not token:
        return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return True
    except jwt.ExpiredSignatureError:
        log.warning("JWT expirado")
        return False
    except Exception:
        return False
