import re
from collections.abc import Iterable

SECRET_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "clientcode",
        "client_code",
        "password",
        "pin",
        "totp",
        "api_key",
        "apikey",
        "privatekey",
        "jwttoken",
        "refreshtoken",
        "feedtoken",
    }
)
SAFE_PROVIDER_CODE = re.compile(r"^[A-Z]{2,4}\d{3,5}$")


def safe_provider_code(value: object) -> str | None:
    candidate = str(value or "").strip().upper()
    return candidate if SAFE_PROVIDER_CODE.fullmatch(candidate) else None


def sanitize_exception(_: BaseException) -> tuple[str, None]:
    return "provider-exception", None


def contains_sensitive_value(text: str, values: Iterable[str]) -> bool:
    return any(value and value in text for value in values)
