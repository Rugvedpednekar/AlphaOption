# Market Data Source Decision

## Decision

AlphaOption will use Angel One SmartAPI as its initial broker-market-data provider, behind a provider-independent interface. Phase 2A does not connect to SmartAPI and requires no credentials. NSE official reports or appropriately licensed vendors may supplement gaps after legal, licensing, retention, and redistribution review. Scraping NSE webpages is explicitly excluded.

## Capability matrix

Status terms: **verified** means exercised against documented provider behavior; **not-testable** means the bounded probe could not lawfully or technically exercise it; **unverified** lacks sufficient evidence; **unavailable** means observed evidence establishes that the source does not provide it in the intended interface.

| Capability | SmartAPI | NSE official reports | Licensed vendor |
| --- | --- | --- | --- |
| Nifty spot candles | Not-testable after evidence-identity review | Unverified | Unverified |
| Nifty futures candles | Not-testable after selector review | Unverified | Unverified |
| Current option candles | Not-testable after selector review | Unverified | Unverified |
| Expired option candles | Not-testable | Unverified | Unverified |
| Volume | Verified as a returned candle field | Unverified | Unverified |
| Open interest | General operation verified; Nifty-specific result not-testable | Unverified | Unverified |
| Bid/ask quotes | General current FULL operation verified; historical not-testable | Unavailable in end-of-day reports | Unverified |
| Instrument metadata | Nifty-specific discovery not-testable after selector review | Unverified | Unverified |

No claim is made that SmartAPI supplies expired-option history until an authorized, reproducible credentialed test confirms instrument discovery, date limits, granularity, and returned fields.

## Research integrity

Black–Scholes values can support theoretical checks, Greeks, and sensitivity experiments. Synthetic values cannot replace actual option prices, liquidity, bid/ask spreads, volume, or open interest in an execution-grade backtest and must never be presented as market history.

## Licensing and redistribution

Exchange and provider terms may restrict storage duration, derived datasets, publication, redistribution, and commercial use. Before acquiring data, record the source agreement, permitted users, retention, attribution, and deletion requirements. Raw licensed data must remain outside Git. Only the small, clearly synthetic fixture in this repository may be redistributed with the code.

## Next validation step

The initial Phase 2B probe verified authentication and general candle, volume, historical OI, and current FULL snapshot/depth operations. Review found that the SDK helper retrieved profile data internally, although it was not persisted, and that generic-role evidence cannot prove Nifty 50 derivative identity. Both paths were repaired and published. Phase 2C now provides a provider-independent pipeline verified only with synthetic fixtures and mocked responses. A separately authorized probe remains required for Nifty-specific provider claims. No request was made during Phase 2C implementation, and raw evidence remains ignored.
