import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Protocol
from unittest.mock import patch

import pyotp
import requests

from app.core.config import Settings
from app.smartapi.redaction import safe_provider_code, sanitize_exception

INSTRUMENT_MASTER_URL = (
    "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
)


class SmartApiSdk(Protocol):
    _routes: dict[str, str]

    def _postRequest(self, route: str, params: dict[str, str]) -> dict[str, Any]: ...
    def setAccessToken(self, access_token: str) -> None: ...
    def setRefreshToken(self, refresh_token: str) -> None: ...
    def setFeedToken(self, feed_token: str) -> None: ...
    def terminateSession(self, client_code: str) -> dict[str, Any]: ...
    def getCandleData(self, params: dict[str, str]) -> dict[str, Any]: ...
    def getOIData(self, params: dict[str, str]) -> dict[str, Any]: ...
    def getMarketData(self, mode: str, exchange_tokens: dict[str, list[str]]) -> dict[str, Any]: ...


class SmartApiError(RuntimeError):
    def __init__(self, category: str, provider_code: str | None = None) -> None:
        super().__init__(category)
        self.category = category
        self.provider_code = provider_code


@contextmanager
def suppress_sdk_logs():
    names = ("SmartApi", "SmartApi.smartConnect", "logzero", "logzero_default")
    states = []
    for name in names:
        logger = logging.getLogger(name)
        states.append((logger, logger.disabled))
        logger.disabled = True
    try:
        yield
    finally:
        for logger, disabled in states:
            logger.disabled = disabled


class ReadOnlySmartApiAdapter:
    """Only the five read-only/session operations approved for Phase 2B."""

    def __init__(
        self,
        settings: Settings,
        sdk_factory: Callable[[str], SmartApiSdk] | None = None,
        instrument_get: Callable[..., Any] = requests.get,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._sdk_factory = sdk_factory or self._official_sdk
        self._instrument_get = instrument_get
        self._sleep = sleep
        self._sdk: SmartApiSdk | None = None
        self.request_count = 0
        self.authentication_attempts = 0

    @staticmethod
    def _official_sdk(api_key: str) -> SmartApiSdk:
        with suppress_sdk_logs():
            # The SDK performs an unrelated public-IP lookup at module import.
            # Replace that lookup with a local placeholder; provider calls begin
            # only when an explicitly approved adapter method is invoked.
            with patch("requests.get", return_value=SimpleNamespace(text="127.0.0.1")):
                from SmartApi.smartConnect import SmartConnect, logzero

            # The SDK configures its own file logger in the constructor. Phase 2B
            # owns all reporting, so prevent that unredacted side channel.
            with patch.object(logzero, "logfile", return_value=None):
                return SmartConnect(api_key=api_key, debug=False, disable_ssl=False)

    def _secret(self, name: str) -> str:
        value = getattr(self._settings, name)
        if value is None or not value.get_secret_value().strip():
            raise SmartApiError("configuration-missing")
        return value.get_secret_value().strip()

    def authenticate(self) -> None:
        if self.authentication_attempts >= 2:
            raise SmartApiError("authentication-attempt-limit")
        self.authentication_attempts += 1
        api_key = self._secret("smartapi_api_key")
        client_code = self._secret("smartapi_client_code")
        pin = self._secret("smartapi_pin")
        seed = self._secret("smartapi_totp_secret")
        try:
            totp = pyotp.TOTP(seed).now()
            self._sdk = self._sdk_factory(api_key)
            self._assert_login_only_sdk_contract(self._sdk)
            self.request_count += 1
            with suppress_sdk_logs():
                # smartapi-python 1.5.5 generateSession() calls getProfile().
                # Invoke its pinned login route directly and keep returned tokens
                # only on this short-lived SDK instance.
                response = self._sdk._postRequest(
                    "api.login", {"clientcode": client_code, "password": pin, "totp": totp}
                )
        except SmartApiError:
            self._sdk = None
            raise
        except Exception as exc:
            self._sdk = None
            category, code = sanitize_exception(exc)
            raise SmartApiError(category, code) from None
        if not response.get("status"):
            self._sdk = None
            raise SmartApiError(
                "authentication-rejected", safe_provider_code(response.get("errorcode"))
            )
        data = response.get("data")
        if not isinstance(data, dict):
            self._sdk = None
            raise SmartApiError("provider-invalid-response")
        tokens = tuple(data.get(key) for key in ("jwtToken", "refreshToken", "feedToken"))
        if not all(isinstance(token, str) and token for token in tokens):
            self._sdk = None
            raise SmartApiError("provider-invalid-response")
        access_token, refresh_token, feed_token = tokens
        self._sdk.setAccessToken(access_token)
        self._sdk.setRefreshToken(refresh_token)
        self._sdk.setFeedToken(feed_token)

    @staticmethod
    def _assert_login_only_sdk_contract(sdk: SmartApiSdk) -> None:
        """Fail closed if the pinned SDK's private login contract changes."""
        routes = getattr(sdk, "_routes", None)
        expected_route = "/rest/auth/angelbroking/user/v1/loginByPassword"
        required = ("_postRequest", "setAccessToken", "setRefreshToken", "setFeedToken")
        if (
            not isinstance(routes, dict)
            or routes.get("api.login") != expected_route
            or any(not callable(getattr(sdk, name, None)) for name in required)
        ):
            raise SmartApiError("sdk-contract-mismatch")

    def terminate_session(self) -> bool | None:
        if self._sdk is None:
            return None
        client_code = self._secret("smartapi_client_code")
        try:
            self.request_count += 1
            with suppress_sdk_logs():
                response = self._sdk.terminateSession(client_code)
            return response.get("status") is True
        except Exception:
            return False
        finally:
            self._sdk = None

    def retrieve_instrument_master(self) -> list[dict[str, Any]]:
        self._sleep(1.1)
        self.request_count += 1
        try:
            response = self._instrument_get(INSTRUMENT_MASTER_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            category, code = sanitize_exception(exc)
            raise SmartApiError(category, code) from None
        if not isinstance(data, list):
            raise SmartApiError("provider-invalid-response")
        return data

    def retrieve_historical_candles(self, params: dict[str, str]) -> dict[str, Any]:
        return self._call("getCandleData", params)

    def retrieve_historical_oi(self, params: dict[str, str]) -> dict[str, Any]:
        return self._call("getOIData", params)

    def retrieve_market_snapshot(self, exchange_tokens: dict[str, list[str]]) -> dict[str, Any]:
        if self._sdk is None:
            raise SmartApiError("not-authenticated")
        self._sleep(1.1)
        self.request_count += 1
        try:
            with suppress_sdk_logs():
                return self._sdk.getMarketData("FULL", exchange_tokens)
        except Exception as exc:
            category, code = sanitize_exception(exc)
            raise SmartApiError(category, code) from None

    def _call(self, method: str, params: dict[str, str]) -> dict[str, Any]:
        if self._sdk is None:
            raise SmartApiError("not-authenticated")
        self._sleep(1.1)
        self.request_count += 1
        try:
            with suppress_sdk_logs():
                return getattr(self._sdk, method)(dict(params))
        except Exception as exc:
            category, code = sanitize_exception(exc)
            raise SmartApiError(category, code) from None
