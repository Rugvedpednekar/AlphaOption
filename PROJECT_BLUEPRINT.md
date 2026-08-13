# AlphaOption Project Blueprint

## Project purpose

AlphaOption is a local-first platform for researching, backtesting, replaying, and paper trading Nifty 50 option-buying strategies. It begins with simulated capital of **₹20,000** and prioritizes reproducibility, realistic execution, and loss containment. Local development and verification precede AWS deployment. Live order placement remains disabled.

## Research question

Can a leakage-safe machine-learning system produce sufficiently calibrated `CALL`, `PUT`, and `NO_TRADE` decisions to improve risk-adjusted Nifty 50 option-buying outcomes after realistic spreads, brokerage, taxes, latency, and slippage, compared with transparent baselines?

Success requires out-of-sample stability, controlled drawdown, adequate sample size, operational reliability, and performance net of all modeled costs. Accuracy alone is not a success criterion.

## Scope and non-goals

Initial scope includes Nifty 50 option buying, historical backtesting, accelerated market replay, and live paper trading during Indian market hours. Angel One SmartAPI is the planned source of historical and live market data. All accepted early trades are simulated.

Non-goals include live execution in the initial phases, live option selling, guaranteed returns, high-frequency/colocated execution, multi-broker routing, and treating synthetic prices as observed market evidence. Eventual live trading is gated future work, not an implied capability.

## High-level architecture

```text
Historical files / SmartAPI market data
                 │
       ingestion + validation
                 │
      normalized PostgreSQL data
                 │
     feature/label pipeline ──> model training + registry
                 │                         │
                 └──── shared strategy engine
                              │
                    shared account risk engine
                              │
             ┌────────────────┼────────────────┐
          backtester      replay clock      live feed
             │                │                 │
             └──────── paper broker adapter ───┘
                              │
                trades, metrics, logs, dashboard

Future only: risk-approved intent -> separately gated live broker adapter
```

Domain interfaces isolate clocks, market-data sources, strategies, risk policy, portfolio state, and broker behavior. The same strategy and risk implementations must run in backtest, replay, paper, and any eventual live mode; mode-specific shortcuts may exist only in adapters.

## Data pipeline

1. Acquire versioned instrument masters, underlying candles/ticks, option quotes/trades, expiries, strikes, and market calendars.
2. Store immutable raw observations with source, exchange timestamp, receipt timestamp, and ingestion metadata.
3. Validate schema, uniqueness, ordering, gaps, timezone, expiry/strike mapping, and anomalous prices/volumes.
4. Normalize to canonical contracts and time bars without using future information.
5. Build point-in-time features and labels under versioned definitions.
6. Produce reproducible train/validation/test datasets with manifests and hashes.

SmartAPI integrations must respect rate limits, reconnect safely, expose connection health, and never log authentication material.

## Database domains

- Reference: instruments, contracts, expiries, strikes, market calendar.
- Market data: underlying bars, option trades/quotes, bid/ask depth where available.
- Research: dataset manifests, feature definitions, labels, splits, experiments, model versions, metrics.
- Trading simulation: signals, rejected-signal reasons, orders, fills, positions, cash ledger, fees, P&L, drawdown.
- Operations: replay sessions, connection health, heartbeats, structured audit events, redacted logs.

Raw data is append-only. Derived records carry lineage and configuration versions. Monetary and quantity fields use explicit precision; timestamps are timezone-aware.

## Feature engineering

Candidate features include point-in-time returns, volatility, trend/momentum, range, volume/liquidity, time of day, expiry proximity, strike/moneyness, spread, quote freshness, and—when observed or defensibly derived—Greeks and implied volatility. Features must declare lookback, availability time, missing-data behavior, and normalization scope. Any fit transformation is learned only from the training window.

## Labels and model design

Labels reflect executable, cost-adjusted forward outcomes for `CALL`, `PUT`, and `NO_TRADE`, using only information available after the decision timestamp to score the outcome. Neutral/abstention thresholds are explicit. Initial baselines include deterministic rules, logistic regression, and tree ensembles; LightGBM/XGBoost follow only after baselines. Probability calibration and decision thresholds are tuned inside training/validation boundaries, never on the final test period.

Black–Scholes synthetic data may support unit tests or controlled sensitivity experiments, but cannot be presented as equivalent to historical option-market prices or quotes and cannot establish real-world profitability.

## Leakage-safe validation

Evaluation uses chronological walk-forward validation. Training precedes validation, which precedes test. Purging removes observations whose label horizons overlap an adjacent split; an embargo separates boundaries. Shuffled cross-validation is prohibited. Contract selection, feature scaling, imputation, threshold tuning, and model selection are fit within each permitted training window. A final untouched chronological holdout is evaluated once after design choices are frozen.

## Event-driven backtesting

The backtester advances an exchange-time clock and processes market data, signal generation, account-level risk checks, orders, fills, portfolio updates, and metrics as ordered events. Final option-strategy evaluation must use real historical option prices or quotes. Fill simulation incorporates bid/ask spreads, liquidity/quote freshness, brokerage, statutory taxes/charges, latency, partial/non-fills when appropriate, and configurable slippage. Reports include assumptions and data limitations.

## Market replay

Replay streams historical events through production-compatible interfaces at configurable speed, with pause, resume, step, and deterministic reset. It uses the shared strategy, risk engine, paper broker, and observability paths. Replay must preserve exchange ordering and must not expose future events to consumers.

## Paper trading

Live paper mode consumes live market data but routes every accepted order intent to the paper broker. It should eventually operate throughout Indian market hours with startup readiness checks, heartbeat/reconnect behavior, stale-data rejection, end-of-day reconciliation, and durable audit records. No code path in early phases may send an order to SmartAPI.

## Frontend dashboard

The Next.js dashboard presents model signals and confidence, rejected-signal reasons, simulated orders/trades/positions, realized and unrealized P&L, equity and drawdown, market/broker/database connection health, replay controls, configuration identity, and searchable redacted system logs. Paper mode and any future live mode must be unmistakably labeled. Recharts provides time-series and distribution views; accessibility and responsive behavior are tested.

## Risk engine

Every simulated trade is rejected unless account-level validation passes. Checks include mode and global kill switch, available cash/margin, maximum premium per trade, daily loss and drawdown limits, open-position/concentration limits, contract liquidity and maximum spread, quote freshness, allowed session, duplicate-order protection, cooldown/rate limits, and data/connection health. Rejections are structured, persisted, and visible in the dashboard. Risk limits are centrally configured and shared across modes.

## Security requirements

Secrets remain outside source control and are loaded from local environment/secret stores. TOTP seeds are never stored in code, configuration examples, logs, datasets, or fixtures. Logs redact tokens, credentials, account identifiers, and sensitive request fields. Paper and future live credentials/configuration are separated; live execution requires layered explicit gates, restricted permissions, auditability, and manual approval. See `SECURITY.md`.

## Testing strategy

- Unit: feature timing, labels, contract selection, fee calculations, risk rules, portfolio accounting.
- Property/invariant: no negative cash beyond policy, conservation of ledger values, no future-data access.
- Integration: database migrations, ingestion idempotency, adapters, API schemas, reconnect handling.
- Backtest/replay: deterministic golden scenarios, event ordering, spread/slippage and latency behavior.
- Model: purged walk-forward splits, reproducibility, leakage checks, calibration and baseline comparisons.
- Frontend/end-to-end: dashboard states and paper-mode workflows with Playwright.
- Security/operations: secret scanning, log-redaction checks, disabled-live-order assertions, startup health checks.

Pytest covers Python layers and Playwright covers browser workflows. CI will lint, type-check, test, build, and scan without requiring real credentials.

## Future AWS deployment

AWS work begins only after extended local paper evaluation. A future design may use containerized services, managed PostgreSQL, encrypted secret storage, centralized monitoring, backups, least-privilege IAM, and a controlled network egress path. SmartAPI order APIs will eventually require a stable/static outbound IP. Deployment must preserve paper/live isolation, default live execution to off, and support rollback and kill switches. AWS preparation does not authorize live orders.

## Publication and reproducibility

Published results should identify code version, dataset provenance and date ranges, instrument-selection rules, split definitions, random seeds, configurations, cost/slippage/latency assumptions, rejected trades, missing-data handling, and all material limitations. Report multiple walk-forward periods, uncertainty, drawdowns, turnover, and comparisons with simple baselines. Never publish secrets, licensed raw data, or claims that synthetic Black–Scholes prices represent observed option markets.
