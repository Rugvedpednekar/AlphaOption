# Market Data Source Decision

## Decision

AlphaOption will use Angel One SmartAPI as its initial broker-market-data provider, behind a provider-independent interface. Phase 2A does not connect to SmartAPI and requires no credentials. NSE official reports or appropriately licensed vendors may supplement gaps after legal, licensing, retention, and redistribution review. Scraping NSE webpages is explicitly excluded.

## Capability matrix

Status terms: **verified** means exercised against documented provider behavior; **not-testable** means the bounded probe could not lawfully or technically exercise it; **unverified** lacks sufficient evidence; **unavailable** means observed evidence establishes that the source does not provide it in the intended interface.

| Capability | SmartAPI | NSE official reports | Licensed vendor |
| --- | --- | --- | --- |
| Nifty spot candles | Verified for bounded 1-minute/5-minute samples | Unverified | Unverified |
| Nifty futures candles | Verified for one current bounded sample | Unverified | Unverified |
| Current option candles | Verified for one current CE and PE bounded sample | Unverified | Unverified |
| Expired option candles | Not-testable | Unverified | Unverified |
| Volume | Verified as a returned candle field | Unverified | Unverified |
| Open interest | Verified through bounded live-contract historical OI samples | Unverified | Unverified |
| Bid/ask quotes | Verified for one current FULL snapshot; historical not-testable | Unavailable in end-of-day reports | Unverified |
| Instrument metadata | Verified for current spot, future, CE, and PE discovery | Unverified | Unverified |

No claim is made that SmartAPI supplies expired-option history until an authorized, reproducible credentialed test confirms instrument discovery, date limits, granularity, and returned fields.

## Research integrity

Black–Scholes values can support theoretical checks, Greeks, and sensitivity experiments. Synthetic values cannot replace actual option prices, liquidity, bid/ask spreads, volume, or open interest in an execution-grade backtest and must never be presented as market history.

## Licensing and redistribution

Exchange and provider terms may restrict storage duration, derived datasets, publication, redistribution, and commercial use. Before acquiring data, record the source agreement, permitted users, retention, attribution, and deletion requirements. Raw licensed data must remain outside Git. Only the small, clearly synthetic fixture in this repository may be redistributed with the code.

## Next validation step

Phase 2B verified bounded current-instrument discovery, candles, volume, live-contract historical OI, and current FULL snapshot/depth fields. Expired-contract discovery, historical bid/ask, maximum retention, and licensing remain unresolved. Phase 2C may be planned only after explicit approval and a lawful retention/licensing decision; Phase 2B adds no WebSockets, general ingestion, feature engineering, ML, backtesting, or order functionality.
