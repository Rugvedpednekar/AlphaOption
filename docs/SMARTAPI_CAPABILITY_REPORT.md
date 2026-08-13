# SmartAPI Capability Report

## Probe summary

One explicitly acknowledged, bounded, sequential, read-only probe ran on
2026-08-13 at 21:07:26 UTC (2026-08-14 at 02:37:26 Asia/Kolkata).

- Official SDK: `smartapi-python==1.5.5`
- TOTP implementation: `pyotp==2.9.0`
- Authentication: verified in one attempt
- Sanitized provider errors: none
- Provider requests: 14, including the SDK's safe profile request and logout
- Session termination: verified
- Rate limiting: not observed; limits were not stress-tested
- Evidence: ignored redacted file at `artifacts/smartapi-probes/probe-2026-08-13T21-07-26.597663_00-00.json`
- Orders sent: zero
- WebSockets opened: zero
- Restricted account operations: zero
- Database ingestion: none

## Capability matrix

| Capability | Status | Observed evidence |
| --- | --- | --- |
| Authentication | Verified | Session created in one attempt and terminated successfully |
| Nifty spot discovery | Verified | Generic `nifty_spot` role selected deterministically |
| Current Nifty future discovery | Verified | Generic `current_future` role selected deterministically |
| Current Nifty CE discovery | Verified | Generic `current_call` role selected deterministically |
| Current Nifty PE discovery | Verified | Generic `current_put` role selected deterministically |
| Expired future discovery | Not-testable | No documented expired identifier was discovered by the bounded probe |
| Expired option discovery | Not-testable | No documented expired identifier was discovered by the bounded probe |
| Recent spot 1-minute candles | Verified | 750 six-field rows; timestamps covered two recent sessions |
| Recent spot 5-minute candles | Verified | 150 six-field rows; timestamps covered two recent sessions |
| Older bounded spot lookback | Verified | 1,500 six-field rows across the conservative 28-day requested range |
| Current future 5-minute candles | Verified | 77 six-field rows returned |
| Current CE 5-minute candles | Verified | 150 six-field rows returned |
| Current PE 5-minute candles | Verified | 71 six-field rows returned |
| OHLC fields | Verified | Present in every tested candle response |
| Historical volume field | Verified | Present in every tested candle response; quantities not retained |
| Historical OI operation | Verified | Present and non-null for the current future, CE, and PE samples |
| Current FULL snapshot | Verified | Four generic roles returned field categories for LTP, volume, and OI |
| Current bid/ask and depth | Verified | Bid, ask, and depth field categories were present in the bounded snapshot |
| Historical bid/ask | Not-testable | Current snapshot depth does not establish historical depth availability |

## Timestamp coverage and intervals

`ONE_MINUTE` and `FIVE_MINUTE` were tested. Recent requests covered
2026-08-11 through 2026-08-13; returned timestamps covered the 2026-08-12 and
2026-08-13 sessions. The conservative older spot request covered 2026-07-14
through 2026-08-11; returned timestamps ran from 2026-07-15 through
2026-08-11. These observations demonstrate only the bounded ranges tested and
do not establish maximum retention.

The market was closed when the FULL snapshot was requested. Field-category
availability was verified, but the probe makes no freshness or live-market
quality claim and retained no prices or quantities.

## Safety, evidence, and limitations

The ignored evidence contains generic roles, statuses, row counts, timestamp
bounds, field-presence booleans, request count, authentication result, and
termination status. It contains no credentials, generated TOTP, tokens,
account identifiers, headers, cookies, instrument tokens, complete symbols,
raw responses, complete instrument records, prices, or quantities. Leakage
and repository scans passed after execution. No WebSocket or restricted
account operation was invoked, and no genuine data was stored in PostgreSQL.

Provider/exchange licensing, permitted retention, derived-data rights,
publication, redistribution, attribution, and deletion obligations remain
unresolved. API access does not establish storage or redistribution rights.
No trading-performance conclusion can be made from this capability probe or
the synthetic fixture. No orders were sent.
