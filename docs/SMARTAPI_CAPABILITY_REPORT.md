# SmartAPI Capability Report

## Initial probe summary and review correction

One explicitly acknowledged, bounded, sequential, read-only probe ran on
2026-08-13 at 21:07:26 UTC (2026-08-14 at 02:37:26 Asia/Kolkata).

- Official SDK: `smartapi-python==1.5.5`
- TOTP implementation: `pyotp==2.9.0`
- Authentication: verified in one attempt
- Sanitized provider errors: none
- Provider requests: 14, including an unintended profile request made internally by the
  pinned SDK's `generateSession()` helper and the final logout
- Session termination: verified
- Rate limiting: not observed; limits were not stress-tested
- Evidence: ignored redacted file at `artifacts/smartapi-probes/probe-2026-08-13T21-07-26.597663_00-00.json`
- Orders sent: zero
- WebSockets opened: zero
- Restricted account operations: zero
- Database ingestion: none

The profile response was not persisted, logged, or included in evidence. Review nevertheless
found that retrieving it violated the Phase 2B account-data boundary. The adapter now uses a
guarded login-only route tied to the pinned SDK contract and no longer calls `generateSession()`.
No provider request was made during this repair.

The initial selector also accepted broad NIFTY-family substrings. Because the redacted evidence
retained generic roles only, it cannot retroactively prove that derivative samples were Nifty 50.
The repaired selector requires the exact Nifty 50 spot identity, exact normalized `NIFTY`
derivative identity, valid non-expired contracts, and CE/PE expiry alignment. A new separately
authorized bounded probe is required before Nifty-specific discovery or derivative capability is
claimed.

## Capability matrix after review

| Capability | Status | Observed evidence |
| --- | --- | --- |
| Authentication | Verified | Session created in one attempt and terminated successfully |
| Nifty spot discovery | Not-testable | Initial evidence retained only a generic role; repaired exact selector has not contacted the provider |
| Current Nifty future discovery | Not-testable | Initial broad selector cannot conclusively establish Nifty 50 identity |
| Current Nifty CE discovery | Not-testable | Initial broad selector cannot conclusively establish Nifty 50 identity or expiry alignment |
| Current Nifty PE discovery | Not-testable | Initial broad selector cannot conclusively establish Nifty 50 identity or expiry alignment |
| Expired future discovery | Not-testable | No documented expired identifier was discovered by the bounded probe |
| Expired option discovery | Not-testable | No documented expired identifier was discovered by the bounded probe |
| Nifty spot 1-minute/5-minute candles | Not-testable | General index candle operations returned data, but the generic evidence does not prove exact Nifty 50 identity |
| Nifty older bounded spot lookback | Not-testable | General index lookback returned data, but exact Nifty 50 identity is not proven |
| Nifty future 5-minute candles | Not-testable | General derivative candle operation worked, but Nifty 50 identity is not proven by retained evidence |
| Nifty CE 5-minute candles | Not-testable | General option candle operation worked, but Nifty 50 identity is not proven by retained evidence |
| Nifty PE 5-minute candles | Not-testable | General option candle operation worked, but Nifty 50 identity is not proven by retained evidence |
| OHLC fields | Verified | Present in every tested candle response |
| Historical volume field | Verified | Present in every tested candle response; quantities not retained |
| Historical OI operation | Verified generally | Returned fields for generic derivative samples; Nifty-specific OI remains not-testable |
| Current FULL snapshot | Verified generally | Generic samples returned LTP, volume, and OI field categories |
| Current bid/ask and depth | Verified generally | Generic samples returned bid, ask, and depth field categories |
| Historical bid/ask | Not-testable | Current snapshot depth does not establish historical depth availability |

## Timestamp coverage and intervals

`ONE_MINUTE` and `FIVE_MINUTE` general candle operations were tested. Recent requests covered
2026-08-11 through 2026-08-13; returned timestamps covered the 2026-08-12 and
2026-08-13 sessions. The conservative older spot request covered 2026-07-14
through 2026-08-11; returned timestamps ran from 2026-07-15 through
2026-08-11. These observations demonstrate only the bounded ranges tested and
do not establish exact Nifty 50 identity or maximum retention.

The market was closed when the FULL snapshot was requested. Field-category
availability was verified, but the probe makes no freshness or live-market
quality claim and retained no prices or quantities.

## Safety, evidence, and limitations

The ignored evidence remains ignored and contains generic roles, statuses, row counts, timestamp
bounds, field-presence booleans, request count, authentication result, and
termination status. It contains no credentials, generated TOTP, tokens,
account identifiers, headers, cookies, instrument tokens, complete symbols,
raw responses, complete instrument records, prices, or quantities. Leakage
and repository scans passed after execution. No WebSocket or restricted
account operation was invoked, and no genuine data was stored in PostgreSQL.

Provider/exchange licensing, permitted retention, derived-data rights,
publication, redistribution, attribution, and deletion obligations remain
unresolved. API access does not establish storage or redistribution rights.
No backtesting or trading-performance conclusion can be made from this capability probe or
the synthetic fixture. No orders were sent.
