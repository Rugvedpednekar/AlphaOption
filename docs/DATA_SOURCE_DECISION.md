# Market Data Source Decision

## Decision

AlphaOption will use Angel One SmartAPI as its initial broker-market-data provider, behind a provider-independent interface. Phase 2A does not connect to SmartAPI and requires no credentials. NSE official reports or appropriately licensed vendors may supplement gaps after legal, licensing, retention, and redistribution review. Scraping NSE webpages is explicitly excluded.

## Capability matrix

Status terms: **verified** means exercised against documented provider behavior; **credential-test-required** needs an authorized account test; **unverified** lacks sufficient evidence; **unavailable** means the source does not provide it in the intended interface.

| Capability | SmartAPI | NSE official reports | Licensed vendor |
| --- | --- | --- | --- |
| Nifty spot candles | Credential-test-required | Unverified | Unverified |
| Nifty futures candles | Credential-test-required | Unverified | Unverified |
| Current option candles | Credential-test-required | Unverified | Unverified |
| Expired option candles | Credential-test-required | Unverified | Unverified |
| Volume | Credential-test-required | Unverified | Unverified |
| Open interest | Credential-test-required | Unverified | Unverified |
| Bid/ask quotes | Credential-test-required | Unavailable in end-of-day reports | Unverified |
| Instrument metadata | Credential-test-required | Unverified | Unverified |

No claim is made that SmartAPI supplies expired-option history until an authorized, reproducible credentialed test confirms instrument discovery, date limits, granularity, and returned fields.

## Research integrity

Black–Scholes values can support theoretical checks, Greeks, and sensitivity experiments. Synthetic values cannot replace actual option prices, liquidity, bid/ask spreads, volume, or open interest in an execution-grade backtest and must never be presented as market history.

## Licensing and redistribution

Exchange and provider terms may restrict storage duration, derived datasets, publication, redistribution, and commercial use. Before acquiring data, record the source agreement, permitted users, retention, attribution, and deletion requirements. Raw licensed data must remain outside Git. Only the small, clearly synthetic fixture in this repository may be redistributed with the code.

## Next validation step

Phase 2B should perform a credentialed capability probe in an approved local environment, save only redacted capability evidence, and update this matrix. It must not add live WebSockets, feature engineering, ML, backtesting, or order functionality.
