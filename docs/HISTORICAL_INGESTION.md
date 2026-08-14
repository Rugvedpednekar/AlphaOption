# Phase 2C Historical Ingestion

## Architecture

The Phase 2C pipeline is provider-independent: a validated request is divided into deterministic UTC chunks, a read-only provider returns candles sequentially, and the ingestion service validates and stores them in the Phase 2A `market_candles` table. Every executed request creates a finalized `ingestion_runs` audit. APIs and the dashboard read stored summaries only; they never trigger ingestion.

## Supported data and time rules

Only `ONE_MINUTE` and `FIVE_MINUTE` OHLCV candles are accepted. Open interest is optional. Requests require an existing instrument ID plus explicit timezone-aware start and end timestamps. Timestamps and returned rows are normalized to UTC. Empty, inverted, future, naive, or longer-than-366-day requests are rejected.

Authorized ranges are represented as half-open intervals and split without overlap or omission: one-minute data uses conservative 7-day chunks and five-minute data uses 30-day chunks. SmartAPI's inclusive end parameter is reduced by one interval at the adapter boundary. These are local safety limits, not claims about provider retention. Chunks are requested sequentially with a configurable delay. The deterministic fixture produces clearly synthetic rows for local development and tests.

## Validation, idempotency, and conflicts

OHLC values must be finite and non-negative, high/low relationships must be possible, and volume/open interest cannot be negative. Zero prices and zero volume are accepted because zero can represent a valid provider observation; downstream quality policy may classify such rows more strictly later. Malformed rows, out-of-range timestamps, duplicate rows within one provider response, unexpected intervals, and conflicting instrument metadata are rejected. The Phase 2A uniqueness key is authoritative under concurrent writes; uniqueness races are classified as identical duplicates or conflicting-candle rejections. A stored timestamp whose values change is never silently overwritten.

Instruments must already exist and be active. Provider, exchange, and token returned with each candle must match the registered row, preventing silent token reassignment. SmartAPI Nifty rows additionally use the Phase 2B exact identity rules. Other NIFTY-family products and expired derivatives are rejected. Expired-option support is not claimed.

## Auditing, gaps, and APIs

Runs record provider, bounded dataset identity, timestamps, inserted/duplicate/rejected counts, synthetic status, and a sanitized status category. Revision `20260813_0003` adds only the duplicate counter to the Phase 2A audit table because per-run duplicate observations cannot be reconstructed reliably from stored candles. Raw provider payloads and exceptions are never persisted. Coverage and gap summaries are bounded to a paginated instrument set. The `raw_interval_slots` gap method counts every elapsed interval between first and last candles, including overnight, weekend, and holiday periods. It is not an exchange-calendar-aware claim of missing market candles.

## Provider and safety gates

The fixture provider requires no network. The SmartAPI adapter delegates authentication to the repaired Phase 2B profile-free login path, uses a short-lived per-instance session, processes calls sequentially, and terminates the session after success or failure. It has no order, account, profile, portfolio, or WebSocket methods. SmartAPI execution requires `SMARTAPI_ENABLED=true`, paper mode, live orders disabled, `--execute`, and `--acknowledge-read-only`. Automated verification keeps SmartAPI disabled and uses mocks only. A genuine provider request requires separate authorization.

## Known limitations

- SmartAPI retention limits, licensing, redistribution rights, and expired-contract availability remain unresolved.
- Gap counts do not yet exclude exchange closures or session boundaries.
- Fixture data does not model genuine prices, liquidity, spreads, outages, or provider corrections.
- Synthetic fixture data cannot support profitability, backtesting, or performance conclusions.
