# AlphaOption Implementation Plan

Each phase retains the safety invariant `ENABLE_LIVE_ORDERS=false` until Phase 10 explicitly reviews—but does not automatically enable—live execution.

## Phase 0: Repository and documentation foundation

- **Objectives:** Establish scope, architecture, delivery sequence, security policy, and safe defaults.
- **Deliverables:** Blueprint, implementation plan, progress log, README, `.gitignore`, `.env.example`, and security policy.
- **Tests:** Markdown/repository checks, consistency review, secret-pattern scan, Git diff inspection.
- **Acceptance criteria:** Requested files are versioned; no credentials or application scaffolding; paper mode and disabled live orders are explicit.
- **Dependencies:** Initialized Git repository and agreed product constraints.
- **Known risks:** Documentation drift and ambiguous future live-trading language.

## Phase 1: Local backend/frontend skeleton

- **Objectives:** Create runnable local service boundaries and developer workflow.
- **Deliverables:** FastAPI and Next.js/TypeScript skeletons, PostgreSQL/SQLAlchemy/Alembic setup, Docker Compose, configuration validation, health endpoints, Pytest/Playwright harnesses.
- **Tests:** Lint, type checks, unit smoke tests, migration round trip, frontend build, local health checks.
- **Acceptance criteria:** One command starts local services; paper mode is visibly default; live-order gate is false and asserted.
- **Dependencies:** Phase 0.
- **Known risks:** Toolchain/version mismatch, platform-specific setup, insecure defaults.

## Phase 2: Historical data ingestion

- **Objectives:** Build reliable, point-in-time market/reference data ingestion.
- **Deliverables:** Canonical schemas, file/SmartAPI historical adapters, validators, idempotent jobs, provenance manifests, gap reports.
- **Tests:** Schema/contract tests, duplicate and timezone cases, idempotency, rate-limit/error fixtures.
- **Acceptance criteria:** A bounded sample imports reproducibly with lineage and documented quality results.
- **Dependencies:** Phase 1; legitimate data access and retention terms.
- **Known risks:** Missing option quotes, changing instrument tokens, rate limits, licensing constraints.

## Phase 3: Feature and label pipeline

- **Objectives:** Generate point-in-time features and executable cost-aware three-class labels.
- **Deliverables:** Versioned feature/label definitions, dataset builder, data manifests, no-lookahead guards.
- **Tests:** Boundary/timestamp unit tests, missing-data cases, deterministic rebuilds, leakage assertions.
- **Acceptance criteria:** Identical inputs/config produce identical dataset hashes; every column has availability/lineage metadata.
- **Dependencies:** Phase 2 and agreed horizons/cost policy.
- **Known risks:** Subtle leakage, survivorship bias, sparse contracts, label instability.

## Phase 4: Baseline models and leakage-safe validation

- **Objectives:** Establish honest baselines and chronological model evaluation.
- **Deliverables:** Rules/logistic/tree baselines, purged walk-forward splitter with embargo, calibration, experiment registry, untouched holdout policy.
- **Tests:** Split-overlap tests, reproducibility, training-only preprocessing, metric and calibration checks.
- **Acceptance criteria:** `CALL`/`PUT`/`NO_TRADE` results beat or contextualize baselines across multiple out-of-sample folds without shuffled CV.
- **Dependencies:** Phase 3.
- **Known risks:** Overfitting, regime dependence, class imbalance, threshold mining.

## Phase 5: Event-driven options backtester

- **Objectives:** Evaluate strategies with real option observations and realistic execution.
- **Deliverables:** Event clock, shared strategy/risk interfaces, portfolio ledger, paper fills, spread/brokerage/tax/latency/slippage models, reports.
- **Tests:** Event ordering, accounting invariants, rejected trades, fee/slippage fixtures, deterministic scenarios.
- **Acceptance criteria:** Results reconcile from event log to P&L and disclose all assumptions; Black–Scholes data is not used as market-equivalent evidence.
- **Dependencies:** Phases 2–4 and adequate historical option quotes/prices.
- **Known risks:** Optimistic fills, stale quotes, incomplete charges, corporate/exchange-rule changes.

## Phase 6: Dashboard and reporting

- **Objectives:** Make decisions, risk outcomes, performance, and health observable.
- **Deliverables:** API/read models and dashboard views for signals, rejection reasons, trades, P&L, drawdown, connection health, and redacted logs.
- **Tests:** API schemas, component/accessibility tests, Playwright workflows, large/empty/error states.
- **Acceptance criteria:** A user can trace any simulated trade or rejection and reconcile headline metrics.
- **Dependencies:** Phases 1 and 5.
- **Known risks:** Misleading aggregates, sensitive logs, slow queries, unclear mode labeling.

## Phase 7: Historical market replay

- **Objectives:** Exercise production-compatible behavior against accelerated historical events.
- **Deliverables:** Replay clock/controller, pause/resume/step/reset, speed controls, deterministic session records.
- **Tests:** Ordering and no-future-access tests, speed independence, restart/replay determinism, UI controls.
- **Acceptance criteria:** Replay produces the same decisions/accounting as equivalent backtest inputs within documented semantics.
- **Dependencies:** Phases 5–6.
- **Known risks:** Clock races, nondeterministic async processing, event backpressure.

## Phase 8: SmartAPI live market data and paper broker

- **Objectives:** Consume live data safely while simulating every order.
- **Deliverables:** Authentication/session and streaming data adapters, reconnect/heartbeat handling, quote freshness policy, paper broker, end-of-day reconciliation.
- **Tests:** Mocked authentication, disconnect/reconnect, stale/out-of-order data, market-hours and live-order prohibition tests.
- **Acceptance criteria:** Complete paper sessions run during Indian market hours without any live order API call; health and logs are visible.
- **Dependencies:** Phases 5–7, SmartAPI access, secure local secret setup.
- **Known risks:** API changes, network loss, clock skew, token expiry, inadvertent order endpoint use.

## Phase 9: Extended paper-trading evaluation

- **Objectives:** Measure robustness across regimes and validate operations over an extended period.
- **Deliverables:** Evaluation protocol, daily reports, drift/reliability metrics, incident log, go/no-go evidence package.
- **Tests:** Long-run soak, recovery, data completeness, ledger reconciliation, alert and kill-switch drills.
- **Acceptance criteria:** Predetermined sample duration and reliability/risk thresholds are met with no unresolved critical incidents; otherwise remain in paper mode.
- **Dependencies:** Phase 8 and sustained market sessions.
- **Known risks:** Insufficient sample, regime shifts, operational gaps, selection bias.

## Phase 10: AWS preparation and gated live execution

- **Objectives:** Prepare secure deployment and separately assess whether tightly gated live buying can ever be authorized.
- **Deliverables:** AWS architecture, static outbound IP for SmartAPI order APIs, IAM/secrets/monitoring/backups, deployment/rollback runbooks, independent live-adapter review and layered gates.
- **Tests:** Infrastructure policy/security checks, disaster recovery, paper deployment soak, order-endpoint denial by default, kill-switch drills.
- **Acceptance criteria:** AWS paper mode is stable; security/risk approvals are documented; live remains disabled unless a separate explicit authorization and release process succeeds.
- **Dependencies:** Phase 9, compliance/broker review, budget, explicit owner approval.
- **Known risks:** Financial loss, credential compromise, cloud/network failure, regulatory/broker policy changes, static-egress misconfiguration.
