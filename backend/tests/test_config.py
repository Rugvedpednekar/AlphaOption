import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_live_orders_are_rejected() -> None:
    with pytest.raises(ValidationError, match="live order execution is not implemented"):
        Settings(enable_live_orders=True)


def test_unknown_trading_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(trading_mode="live")  # type: ignore[arg-type]
