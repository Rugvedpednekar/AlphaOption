AlphaOption — Project Architecture & Structured Blueprint

Status: Planning and local research
Primary market: Nifty 50 index options
Initial modes: Backtest, market replay, and paper trading
Initial capital assumption: ₹20,000 virtual capital
Live orders: Disabled until all safety and validation gates are satisfied

1. Project Summary

AlphaOption is a local-first research and paper-trading platform for evaluating whether machine-learning models contain statistically and economically meaningful information about short-horizon Nifty 50 movements and option-buying opportunities.

The system will collect market data, engineer point-in-time features, train leakage-resistant models, simulate realistic Nifty option trades, and present results through a modern dashboard. It will be developed and verified locally before any AWS deployment or live broker execution is considered.

AlphaOption is not intended to claim that machine learning can reliably predict the market. Its purpose is to test that claim rigorously.

Primary research question

Can machine-learning models identify short-horizon Nifty 50 option-buying opportunities that produce persistent out-of-sample returns after bid–ask spreads, brokerage, taxes, slippage, latency, and risk are included?

Supporting research questions

Do ML models outperform simple momentum, mean-reversion, and no-trade baselines?

Does directional accuracy translate into profitable option trades?

Which market regimes produce useful or harmful signals?

Are results stable across walk-forward periods, expiry cycles, and different cost assumptions?

Does a trade-selection model improve results by rejecting weak directional predictions?

2. Goals

Product goals

Run locally with a single documented startup workflow.

Provide historical backtesting, accelerated market replay, and live paper trading.

Display signals, rejected trades, positions, P&L, drawdown, and system health in a frontend dashboard.

Use the same strategy and risk logic across backtest, replay, paper, and eventual live modes.

Preserve sufficient data and experiment metadata to reproduce every reported result.

Make safety decisions observable: every rejected trade must have a recorded reason.

Research goals

Prevent shuffled-validation and look-ahead leakage.

Compare ML against credible non-ML baselines.

Evaluate economic results after realistic costs, not accuracy alone.

Report negative and positive findings honestly.

Produce reproducible evidence suitable for an independent-study paper or technical report.

Engineering goals

Separate market data, feature generation, strategy decisions, risk, broker execution, and reporting.

Use explicit interfaces so simulated and real brokers cannot be accidentally mixed.

Store timestamps and model versions with every signal and trade.

Fail safely during stale data, API errors, restarts, or inconsistent broker state.

Keep credentials, tokens, market datasets, and generated artifacts out of Git.

3. Non-Goals

The following are out of scope for the initial project:

Live order placement.

Naked option selling.

Automated strategy changes based only on recent profit or loss.

High-frequency or sub-second trading.

Claims of guaranteed returns or accurate future-price prediction.

Training on synthetic option data and presenting it as historical market evidence.

Supporting multiple brokers or asset classes before the Nifty workflow is validated.

Mobile trading controls or unrestricted public access to trading actions.

Averaging down, martingale sizing, or revenge-trading logic.

4. Operating Modes

AlphaOption must have an explicit operating mode. The mode is immutable for the lifetime of a running job.

Mode

Market-data source

Broker

Purpose

Real orders

backtest

Historical dataset

Simulated event broker

Research and evaluation

Never

replay

Historical event stream

Simulated paper broker

Validate live-like behavior

Never

paper

Live SmartAPI feed

Paper broker

Forward testing

Never

live

Live SmartAPI feed

Future Angel One adapter

Gated deployment

Disabled initially

Required defaults:

TRADING_MODE=paper
ENABLE_LIVE_ORDERS=false

The application must refuse live order execution unless a future release implements and satisfies multiple independent safety gates. Changing one environment variable must never be enough to activate live trading.

5. High-Level Architecture

flowchart TD
    A["Market data adapters"] --> B["Immutable raw-data store"]
    B --> C["Point-in-time feature pipeline"]
    C --> D["Model and strategy engine"]
    D --> E["Independent risk engine"]
    E --> F["Broker interface"]
    F --> G["Backtest or paper broker"]
    D --> H["FastAPI application"]
    E --> H
    G --> H
    H --> I["Next.js dashboard"]

Core components

Market-data adapters — historical files, market replay, and SmartAPI live feed.

Raw-data store — append-only market observations with source and quality metadata.

Feature pipeline — point-in-time features calculated only from information available at the decision timestamp.

Model service — versioned probability predictions for CALL, PUT, and NO_TRADE.

Strategy engine — converts model probabilities and trading rules into trade proposals.

Risk engine — independently accepts or rejects every proposal.

Broker interface — common contract for simulated, paper, and future live execution.

Portfolio/accounting engine — positions, cash, costs, realized P&L, unrealized P&L, and drawdown.

FastAPI backend — APIs and server-sent events or WebSockets for the dashboard.

Next.js frontend — operational, research, and risk visibility.

Background workers — ingestion, replay, feature computation, backtests, and paper sessions.

Observability layer — structured logs, health checks, data freshness, metrics, and alerts.

6. Planned Technology Stack

Backend and research

Python 3.12

FastAPI

Pydantic

SQLAlchemy

Alembic

PostgreSQL

Redis, only if job coordination or transient live state requires it

Pandas and/or Polars

NumPy and SciPy

scikit-learn

LightGBM and XGBoost

Optuna, if controlled hyperparameter tuning is later required

PyArrow/Parquet for larger local datasets

Frontend

Next.js with TypeScript

Tailwind CSS

shadcn/ui or an equivalent accessible component system

Recharts for dashboard charts

TanStack Query for API state

Server-Sent Events or WebSockets for live status

Engineering and testing

Docker Compose

Pytest

Ruff

MyPy or Pyright

ESLint

TypeScript strict mode

Playwright

GitHub Actions

Later AWS deployment

EC2 or ECS in the Mumbai region

Elastic IP or another approved static outbound IP mechanism

RDS PostgreSQL or a carefully managed PostgreSQL deployment

S3 for immutable datasets and reports

Secrets Manager or Systems Manager Parameter Store

CloudWatch and notification alarms

AWS is not required for the local research milestones.

7. Suggested Repository Structure

AlphaOption/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── backtesting/
│   │   ├── brokers/
│   │   ├── core/
│   │   ├── data/
│   │   ├── db/
│   │   ├── features/
│   │   ├── models/
│   │   ├── portfolio/
│   │   ├── replay/
│   │   ├── risk/
│   │   ├── strategies/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   └── tests/
├── research/
│   ├── experiments/
│   ├── notebooks/
│   └── reports/
├── scripts/
├── docs/
├── infra/
│   ├── local/
│   └── aws/
├── data/
│   ├── raw/
│   ├── curated/
│   └── samples/
├── models/
├── results/
├── docker-compose.yml
├── .env.example
├── PROJECT_BLUEPRINT.md
├── implementation_plan.md
├── PROJECT_UPDATE.md
├── SECURITY.md
└── README.md

Large data, model binaries, results, logs, and credentials must be ignored by Git. Only small, licensed, non-sensitive samples intended for tests may be committed.

8. Market Data Architecture

Phase 2C operationalizes this architecture with explicit UTC ranges, conservative deterministic chunks, sequential throttled provider calls, registered-instrument identity checks, idempotent Phase 2A storage, conflict rejection, and finalized ingestion-run audits. Its fixture source is synthetic and cannot support performance conclusions. SmartAPI historical execution remains separately authorized and disabled during automated verification.

Data sources

Historical underlying data

Nifty 50 spot/index candles.

Current-month and point-in-time Nifty futures candles.

At least 1-minute and 5-minute intervals where legally and technically available.

Trading calendar, holidays, expiries, and contract metadata.

Historical option data

Final economic evaluation requires actual option observations where possible:

Expiry and strike.

CE/PE type.

Bid and ask prices and quantities.

Last traded price and quantity.

Volume.

Open interest and change in open interest.

Exchange timestamp.

If bid/ask history is unavailable, the limitation must be declared and conservative spread assumptions must be tested. A spot/futures directional backtest is not evidence of option profitability.

Live data accumulation

The live collector will eventually subscribe to:

Nifty spot/index.

Relevant Nifty futures.

A bounded band of strikes around ATM for selected expiries.

Option quotes, volumes, and open interest provided by the feed.

The strike subscription band must update safely as the underlying moves without exceeding documented API or WebSocket limits.

Required timestamps

Every observation should preserve:

exchange_timestamp

received_timestamp

persisted_timestamp

source

instrument_token

trading_symbol

quality_status

All stored timestamps should be timezone-aware. Market rules and session scheduling use Asia/Kolkata; database storage should use UTC with explicit conversion at boundaries.

Raw-data principles

Raw market observations are append-only.

Corrections create new records or auditable correction metadata.

Aggregated candles must be reproducible from lower-level observations where available.

Duplicate messages must be handled idempotently.

Out-of-order data must be detected and recorded.

Stale, crossed, zero, or impossible quotes must be flagged.

Instrument-master snapshots must be preserved by effective date.

9. Initial Database Domains

The exact schema will be designed during implementation, but the domain model should include:

Market and reference data

instruments

instrument_snapshots

trading_sessions

market_ticks

candles

option_quotes

data_quality_events

Research and ML

feature_sets

feature_values or versioned feature datasets

label_definitions

experiments

model_versions

model_metrics

predictions

Trading simulation

strategy_versions

signals

trade_proposals

risk_decisions

orders

fills

positions

portfolio_snapshots

backtest_runs

paper_sessions

Operations

system_events

service_heartbeats

configuration_versions

audit_events

Every prediction, signal, risk decision, order, and fill must be traceable to the exact data, feature definition, model version, strategy version, configuration, and code revision that produced it.

10. Feature Engineering

All features must be point-in-time correct and derived only from information available before the decision is made.

Underlying price features

Lagged returns over multiple horizons.

EMA relationships and slopes.

RSI.

ATR and normalized ATR.

Bollinger-band position and width.

Rolling realized volatility.

Volume-weighted measures where valid volume exists.

Distance from intraday high, low, VWAP, and opening range.

Gap from previous close.

Futures basis and basis change.

Option-chain features

Put–call volume and OI ratios.

Change in put–call ratios.

OI concentration near ATM.

Call and put OI imbalance by moneyness bucket.

Bid–ask spread and depth.

ATM straddle price and change.

Implied-volatility level, skew, and term structure when recoverable from real quotes.

Delta, gamma, theta, and vega calculated from observed option prices and documented assumptions.

Distance to strike and time to expiry.

Time and regime features

Minutes since market open.

Minutes until new-entry cutoff.

Day of week.

Expiry-day and days-to-expiry flags.

Trend/range regime.

Volatility regime.

Opening, midday, and closing-session regimes.

Feature restrictions

No end-of-candle values may be used to simulate an execution at that same candle close.

No full-dataset scaling, imputation, selection, or dimensionality reduction before splitting.

No feature may rely on revised values unavailable at the decision time.

Missingness should be modeled explicitly where meaningful.

Feature definitions must be versioned.

Phase 3 initial implementation scope

The first implemented feature set is deliberately narrower than the long-term catalog. It
accepts one registered, source-homogeneous Nifty 50 `FIVE_MINUTE` candle series with
explicit UTC bounds. A row becomes available only after its candle closes. It includes
lagged simple/log returns, candle shape, EMA 9/21 and slopes, Wilder RSI 14 and ATR 14,
rolling log-return volatility, volume normalization, and Asia/Kolkata session encodings.
Unavailable warm-up values remain null; prices are never interpolated.

Experimental targets are stored distinctly from model-input columns. Fifteen- and
thirty-minute future returns use three/six bars ahead and `up`, `down`, or `neutral` under
the point-in-time threshold `max(0.001, 0.5 * ATR14 / close)`. Targets cannot cross raw
five-minute gaps or Asia/Kolkata trading dates and are unavailable at the dataset tail.
Target construction is not evidence of profitability.

Alembic revision `20260813_0004` adds normalized `feature_runs` and `market_features`
tables with deterministic configuration hashes, source labels, idempotent uniqueness, and
failure auditing. Bounded read-only APIs and the Feature Status dashboard expose aggregate
availability. Black-Scholes, Greeks, PCR, option-chain, synthetic-option, model, backtest,
signal, and trading work remain outside Phase 3.

11. Black–Scholes and Options Mathematics

Black–Scholes–Merton may be used for:

Theoretical option-value checks.

Greek calculations.

Implied-volatility inversion from observed market prices.

Controlled sensitivity experiments.

Data-quality validation.

It must not be used to claim that synthetic premiums reproduce historical market behavior.

Implied volatility requires an observed option price. For an observed call price:

$$
C_{market} = BS(S, K, T, r, q, \sigma_{IV})
$$

The solver estimates $\sigma_{IV}$ such that the model price matches the market price. Without the observed option price, the project may use an assumed or realized-volatility input, but it must not label that input as historical implied volatility.

The pricing module must document:

Risk-free-rate source and effective date.

Dividend-yield assumption.

Day-count convention.

Timezone and time-to-expiry calculation.

Price used for IV inversion: bid, ask, mid, or last.

Handling of invalid, stale, or arbitrage-inconsistent quotes.

12. Prediction and Label Design

Stage 1: Direction model

Estimate the probability of a meaningful underlying move over a defined horizon such as 15 or 30 minutes.

The label threshold must be large enough to represent an economically relevant move, not simply whether the future return is greater than zero.

Stage 2: Trade-selection model

Estimate whether the candidate option trade has positive expected return after spread, costs, slippage, and time decay.

This stage may use:

Direction probabilities.

Expected move magnitude.

Moneyness.

Time to expiry.

Spread and liquidity.

Implied-volatility context.

Greeks.

Time of day and regime.

Final decision classes

CALL

PUT

NO_TRADE

The strategy must not force a CE or PE decision at every evaluation interval.

Labeling approaches to test

Return thresholds with a neutral zone.

Volatility-scaled thresholds.

Triple-barrier labels with profit, stop, and time barriers.

Direct net option-return labels where suitable historical option data exists.

The label horizon, barrier values, execution delay, and cost assumptions must be stored with the experiment.

13. Models and Baselines

Required baselines

Always NO_TRADE.

Random direction with matched trade frequency.

Simple EMA or breakout strategy.

Simple mean-reversion strategy.

Logistic regression.

Previous-period momentum.

Candidate ML models

Logistic regression with regularization.

Random forest as an additional tabular baseline.

LightGBM.

XGBoost.

Deep-learning models are deferred until simpler models show stable value and sufficient data exists. Complexity must be justified by out-of-sample improvement, not novelty.

Probability handling

Evaluate probability calibration.

Consider Platt or isotonic calibration inside training folds only.

Select trade thresholds using validation data only.

Store raw and calibrated probabilities.

Measure whether confidence corresponds to realized outcome frequency.

14. Leakage-Safe Validation

Ordinary shuffled cross-validation is prohibited.

Required evaluation design

Sort all observations chronologically.

Use expanding or rolling walk-forward splits.

Purge overlapping labels from split boundaries.

Apply an embargo where needed.

Fit preprocessing only on each training window.

Tune hyperparameters only within training/validation periods.

Reserve the final period as an untouched test set.

Execute at the next available tradeable quote after signal generation.

Example

Fold

Training

Validation

1

Months 1–6

Month 7

2

Months 1–7

Month 8

3

Months 1–8

Month 9

Final

Selected historical training period

Untouched final test period

Split lengths will depend on actual data volume and regime coverage.

Statistical reporting

Confidence intervals for key metrics.

Bootstrap analysis that respects time dependence where possible.

Multiple-testing awareness.

Performance dispersion across folds.

Sensitivity to thresholds and costs.

Explicit record of every experiment attempted.

15. Event-Driven Backtesting Engine

The final simulator should reproduce the decision sequence rather than simply multiply signals by future returns.

Required event flow

Receive the next historical market event.

Update point-in-time market state.

Complete the relevant bar, if using bars.

Generate features.

Request model probabilities.

Create a trade proposal.

Run independent risk checks.

Select the point-in-time valid option contract.

Submit the simulated order.

Apply latency and fill rules.

Update cash, position, costs, and P&L.

Evaluate stop, target, time stop, and end-of-day exit.

Persist all events and decisions.

Contract selection

The simulator must determine at the decision timestamp:

Valid expiry.

ATM strike based on current rules and instrument data.

CE or PE contract.

Lot size from effective-dated reference data.

Quote freshness.

Spread and liquidity eligibility.

Contract rules must be configuration-driven rather than permanently hard-coded.

Fill model

Default conservative assumptions:

Buy at ask, not mid or last.

Sell at bid.

Apply configurable decision and order latency.

Reject stale or unavailable quotes.

Apply partial-fill logic if depth data supports it.

Record unfilled and rejected orders.

Cost model

Use effective-dated configuration for:

Brokerage.

Exchange transaction charges.

STT.

GST.

Stamp duty.

SEBI/IPFT charges.

Bid–ask spread.

Slippage.

Cost rates must not be treated as permanent because exchange, statutory, broker, and contract rules can change.

16. Risk Engine

Risk validation is independent of model confidence. A high-confidence signal may still be rejected.

Initial paper-trading controls

Virtual starting capital of ₹20,000.

Maximum one open directional position.

Maximum one lot per accepted trade.

Configurable maximum trades per day.

Configurable account-risk budget per trade.

Configurable maximum daily loss.

Maximum permitted bid–ask spread.

Minimum quote freshness and liquidity.

No averaging down.

No martingale sizing.

No new entry after the configured cutoff.

Mandatory intraday square-off.

Consecutive-loss circuit breaker.

Duplicate-order and duplicate-signal protection.

Position sizing

The intended position size is based on account risk:

$$
Quantity = \left\lfloor
\frac{Account\ Equity \times Risk\ Fraction}
{Entry\ Price - Stop\ Price}
\right\rfloor
$$

The result must then be rounded down to an exchange-valid lot quantity. If even one lot exceeds the permitted loss, the risk engine rejects the trade.

Required rejection reasons

Examples include:

INSUFFICIENT_CAPITAL

RISK_BUDGET_EXCEEDED

DAILY_LOSS_LIMIT_REACHED

MAX_TRADES_REACHED

POSITION_ALREADY_OPEN

STALE_MARKET_DATA

SPREAD_TOO_WIDE

INSUFFICIENT_LIQUIDITY

MODEL_CONFIDENCE_TOO_LOW

EXPECTED_VALUE_NOT_POSITIVE

ENTRY_CUTOFF_PASSED

SYSTEM_NOT_HEALTHY

Every rejection must be persisted and visible in the dashboard.

17. Historical Market Replay

Market replay validates whether the event-driven application behaves correctly without waiting for the real market.

Replay requirements

Select a historical trading session.

Replay data in exact chronological order.

Support speeds such as 1x, 5x, 20x, and 100x.

Pause, resume, and stop safely.

Use the same feature, strategy, risk, accounting, and dashboard paths as paper mode.

Simulate session boundaries and mandatory square-off.

Allow deterministic reruns with the same configuration and random seed.

Support restart and recovery tests.

Replay is an operational test, not a substitute for the formal backtest evaluation.

18. Live Paper Trading

Paper mode consumes live market data but never calls a real order endpoint.

Paper broker responsibilities

Validate simulated orders.

Fill buys using ask-side logic and sells using bid-side logic.

Apply configured latency and slippage.

Reject stale or unavailable quotes.

Maintain virtual cash, positions, orders, and fills.

Reconcile internal portfolio state after restarts.

Deduct all configured costs.

Produce the same event types expected from a future live broker adapter.

Forward-testing duration

One profitable week is not sufficient evidence. Advancement should require at least:

8–12 weeks of paper trading, and

100 completed simulated trades,

whichever takes longer. If the strategy trades infrequently, the observation period must be extended.

The period should include expiry and non-expiry days, trend and range conditions, high and low volatility, gaps, data interruptions, and application restarts.

19. Frontend Dashboard

The frontend is an operational and research interface, not a manual day-trading terminal.

Overview page

Current operating mode.

Prominent PAPER TRADING — NO REAL ORDERS banner.

Market status.

Current virtual equity and cash.

Today’s realized and unrealized P&L.

Drawdown and daily risk utilization.

Open position.

SmartAPI/data-feed status.

Last market-event timestamp.

Model, strategy, and configuration versions.

Service health.

Strategy page

Nifty spot and futures values.

Selected expiry and strike.

CALL, PUT, and NO_TRADE probabilities.

Signal confidence and expected-value estimate.

Important feature values.

Accepted/rejected decision.

Human-readable rejection reason.

Backtest page

Date range.

Dataset and model version.

Initial capital.

Strategy/risk configuration.

Cost and slippage assumptions.

Run/cancel status.

Equity curve.

Drawdown curve.

Monthly and daily returns.

Trade distribution.

Baseline comparison.

Downloadable report and trade ledger.

Replay page

Session selector.

Playback speed.

Start, pause, resume, and stop.

Replay clock and progress.

Live simulated signals, orders, fills, and P&L.

Trades page

Signals.

Rejected proposals.

Orders and fills.

Entry and exit prices.

Gross and net P&L.

Costs.

Exit reason.

Model and strategy versions.

System page

Service heartbeats.

Data freshness.

WebSocket/reconnect events.

Worker/job status.

Structured operational logs with secrets redacted.

Active circuit breakers.

Settings page

Only safe research and paper settings may be edited. All changes must be validated, versioned, timestamped, and auditable.

The frontend must never display broker secrets, TOTP values, access tokens, or unredacted authentication errors.

20. API Boundaries

Initial API groups may include:

/api/health
/api/system/status
/api/market/status
/api/backtests
/api/backtests/{id}
/api/replays
/api/replays/{id}
/api/paper/sessions
/api/paper/sessions/{id}
/api/signals
/api/risk-decisions
/api/orders
/api/trades
/api/portfolio
/api/models
/api/configurations
/api/events/stream

Mutating operations must be authenticated in any remotely accessible deployment. Job start/stop endpoints require idempotency and audit records.

21. Performance Evaluation

Classification metrics

Balanced accuracy.

Precision, recall, and F1 by class.

PR-AUC and ROC-AUC where meaningful.

Confusion matrix.

Brier score.

Calibration curve.

Coverage: percentage of observations resulting in trades.

Economic metrics

Gross and net P&L.

Net return.

Maximum drawdown.

Profit factor.

Win rate.

Average and median win/loss.

Expectancy per trade.

Sharpe and Sortino ratios with assumptions documented.

Turnover.

Longest losing streak.

Exposure time.

Costs as a percentage of gross profit.

Stability analysis

Results by walk-forward fold.

Results by month.

Expiry versus non-expiry sessions.

Time-of-day performance.

Trend/range and volatility regimes.

Confidence buckets.

Slippage and spread sensitivity.

Threshold sensitivity.

No single metric determines success. Results must persist after conservative costs and across multiple out-of-sample periods.

22. Testing Strategy

Unit tests

Indicators and feature calculations.

Timezone and session logic.

Expiry/strike selection.

Option mathematics.

Label generation.

Cost calculations.

Position sizing.

Risk-rejection rules.

P&L accounting.

Order-state transitions.

Integration tests

Historical ingestion to database.

Feature pipeline to prediction.

Strategy to risk to simulated broker.

Backtest persistence and report generation.

Replay through frontend event stream.

Paper-broker restart recovery.

Data-quality tests

Duplicate timestamps.

Missing intervals.

Out-of-order events.

Invalid OHLC relationships.

Crossed/negative spreads.

Impossible prices or quantities.

Stale quotes.

Instrument-token consistency.

Frontend tests

Dashboard loading and error states.

Paper-mode safety banner.

Backtest form validation.

Replay controls.

Signal and rejection visibility.

Live event updates.

Accessibility and responsive layout.

Safety tests

Live orders remain impossible in initial releases.

Secrets never appear in logs or APIs.

Daily-loss circuit breaker blocks new trades.

Stale data blocks proposals.

Duplicate signals cannot create duplicate orders.

Restart recovery preserves correct simulated position state.

23. Security Requirements

Never commit .env files, API credentials, client codes, passwords, TOTP seeds, access tokens, refresh tokens, or feed tokens.

Use placeholders only in .env.example.

Redact authentication headers and sensitive SDK errors from logs.

Use least-privilege database and cloud identities.

Keep PostgreSQL and Redis inaccessible from the public internet.

Require authentication and HTTPS for any remotely accessible dashboard.

Make operational controls auditable.

Rotate any secret immediately if it is exposed.

Keep raw market data, logs, and model artifacts outside Git.

Run automated secret scanning in CI.

The future live broker adapter must be isolated from research notebooks and frontend code.

24. Reliability and Observability

Health signals

Market-feed connection.

Last valid quote time.

Database availability.

Worker heartbeat.

Active mode.

Current session state.

Model loaded/version.

Risk engine state.

Broker adapter state.

Operational events

Connection and authentication lifecycle.

Reconnect attempts.

Rate limiting.

Dropped or stale messages.

Signal generation.

Risk acceptance/rejection.

Order/fill state changes.

Circuit-breaker activation.

Session start and square-off.

Graceful and abnormal shutdown.

Logs should be structured, timestamped, correlated by request/session/job ID, and redacted.

25. Local Development Workflow

The target local workflow is:

docker compose up --build

Expected local services:

Frontend: http://localhost:3000

Backend/API docs: http://localhost:8000/docs

PostgreSQL: internal Docker network only unless explicitly required for development

Local development must support Windows with Docker Desktop because the initial development environment is Windows-based.

Each milestone should end with:

Tests and validation.

Update to PROJECT_UPDATE.md.

Review of Git changes and secret scan.

Intentional commit message.

Push to GitHub.

26. Future AWS Architecture

AWS deployment is considered only after local backtesting, replay, and extended paper trading are stable.

Planned properties

Deployment in or near India for reasonable market-data latency.

Static outbound IP approved and whitelisted for future order APIs.

Private database networking.

Managed secret storage.

Encrypted storage and backups.

Centralized logging and alarms.

Automated service restart with position-aware recovery.

Read-only dashboard views separated from sensitive trading controls.

The first AWS deployment should remain paper-only. Cloud hosting does not automatically authorize live execution.

27. Live-Execution Gate

Live execution is a future, separately reviewed phase. It cannot be activated merely because paper trading was profitable for a few days.

Before any live option-buying release, require documented evidence of:

Leakage-controlled backtests on actual tradeable option data.

Positive net expectancy under conservative cost assumptions.

Stability across out-of-sample folds and market regimes.

At least 8–12 weeks and 100 completed paper trades, whichever takes longer.

Correct handling of disconnects, stale data, restarts, and duplicate events.

Broker-position reconciliation.

Verified risk limits and emergency shutdown.

Credential and deployment security review.

Current broker, exchange, and regulatory requirement review.

Explicit manual approval for a specific release and account.

The initial live system, if approved later, should begin with the minimum valid exposure and option buying only. Option selling requires a separate strategy, margin model, tail-risk analysis, and approval process. Defined-risk spreads are preferred over naked selling.

28. Publication and Reproducibility

Every publishable experiment should record:

Git commit hash.

Dataset version and date range.

Instrument universe.

Feature-set version.

Label definition.

Model and hyperparameters.

Training/validation/test windows.

Random seeds.

Strategy and risk configuration.

Cost model version.

Metrics and artifacts.

Known data limitations.

The paper should distinguish clearly among:

Directional predictive performance.

Simulated option performance.

Paper-trading performance.

Any eventual live performance.

Negative results remain valid research findings when the methodology is rigorous and reported honestly.

29. Phased Roadmap

Phase

Name

Main outcome

0

Repository foundation

Documentation, security rules, and project governance

1

Local application skeleton

FastAPI, Next.js, PostgreSQL, Docker Compose, health checks

2

Historical ingestion

Validated point-in-time spot/futures/option datasets

3

Features and labels

Versioned, leakage-safe research datasets

4

Baseline modeling

Walk-forward evaluation against simple baselines

5

Options backtester

Event-driven execution, accounting, costs, and reports

6

Dashboard

Research and operational visibility

7

Market replay

Live-like deterministic historical sessions

8

SmartAPI paper mode

Live feed with simulated execution only

9

Extended paper evaluation

Multi-regime forward-test evidence

10

AWS paper deployment

Always-on, monitored, static-network-ready system

11

Gated live option buying

Separate approval after every prior gate passes

Each phase will have detailed deliverables, tests, acceptance criteria, dependencies, and risks in implementation_plan.md.

30. Definition of Project Success

AlphaOption succeeds if it produces an honest, reproducible answer to its research question and a reliable local platform for observing that evidence.

Success does not require a profitable model. A well-supported negative result is more valuable than a profitable-looking result produced by leakage, unrealistic fills, or ignored costs.

The engineering system is considered successful when:

The same strategy path runs in backtest, replay, and paper modes.

Every trade and rejection is reproducible and explainable.

Results include realistic market friction.

Risk controls work under failure conditions.

The dashboard provides trustworthy operational visibility.

No live order can be placed by the initial release.

31. Immediate Next Step

Complete and verify the Phase 0 documentation foundation, then begin Phase 1 with:

FastAPI health and system-status endpoints.

Next.js dashboard shell with a paper-trading banner.

PostgreSQL and Alembic initialization.

Docker Compose local startup.

Backend, frontend, and container smoke tests.

No trading strategy, broker authentication, or order code should be added until the local foundation is stable.

Disclaimer

AlphaOption is an educational and research project. Backtests and paper-trading results do not guarantee future performance. Options can lose value rapidly and may result in the loss of the entire premium paid. Any eventual use of real capital requires independent judgment, current regulatory and broker verification, and acceptance of financial risk by the account owner.
