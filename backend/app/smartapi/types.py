from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

CapabilityStatus = Literal[
    "verified",
    "unavailable",
    "not-testable",
    "provider-error",
    "credential/configuration-error",
]


@dataclass(frozen=True)
class ProbeInstrument:
    role: str
    exchange: str
    token: str
    symbol: str
    expiry: date | None = None
    strike: float | None = None
    instrument_type: str = ""


@dataclass(frozen=True)
class CapabilityResult:
    capability: str
    status: CapabilityStatus
    details: dict[str, Any] = field(default_factory=dict)
    provider_code: str | None = None


@dataclass(frozen=True)
class ProbeReport:
    started_utc: str
    completed_utc: str
    sdk_version: str
    provider_request_count: int
    authentication: CapabilityResult
    capabilities: tuple[CapabilityResult, ...]
    instruments: tuple[str, ...]
    intervals: tuple[str, ...]
    session_terminated: bool | None
    orders_sent: bool = False
