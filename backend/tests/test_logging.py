from app.core.logging import REDACTED, redact


def test_sensitive_logging_fields_are_redacted() -> None:
    payload = redact(
        {
            "operating_mode": "paper",
            "authorization": "Bearer unsafe",
            "nested": {"totp_secret": "unsafe", "status": "healthy"},
        }
    )
    assert payload == {
        "operating_mode": "paper",
        "authorization": REDACTED,
        "nested": {"totp_secret": REDACTED, "status": "healthy"},
    }
