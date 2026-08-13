# AlphaOption Implementation Plan

This plan implements the roadmap in `PROJECT_BLUEPRINT.md`. Status values are intentionally conservative: **Phase 0 is in progress; Phases 1–11 are pending.** Live orders remain disabled unless Phase 11 is separately reviewed and explicitly approved.

## Phase 0: Repository foundation

**Status:** Completed

- **Objective:** Establish project governance, scope, safety defaults, architecture, and a reproducible delivery plan without application code.
- **Deliverables:** `PROJECT_BLUEPRINT.md`, this plan, `PROJECT_UPDATE.md`, `README.md`, `.gitignore`, `.env.example`, and `SECURITY.md`.
- **Detailed tasks:** Align all documents with the blueprint; document Phases 0–11; define paper-only defaults; exclude secrets, datasets, and generated artifacts; review encoding and terminology.
- **Tests and verification:** Read all documentation; check required headings and phase fields; run `git diff --check`; scan for high-confidence secret patterns and sensitive filenames; inspect Git status and diff summary.
- **Acceptance criteria:** All Phase 0 files are committed on `main`; documentation is internally consistent and readable as UTF-8; no application scaffolding, credentials, or live-order capability exists.
- **Dependencies:** Initialized Git repository and approved blueprint.
- **Risks:** Documentation drift, accidental secret inclusion, unclear paper/live boundaries, platform-specific text encoding.
- **Completion checklist:** [x] Blueprint established; [x] supporting files drafted; [x] final checks complete; [x] Phase 0 commit pushed; [x] progress log updated to completed.

## Phase 1: Local application skeleton

**Status:** Completed

- **Objective:** Create a reliable Windows-compatible local development foundation.
- **Deliverables:** FastAPI service, Next.js/TypeScript dashboard shell, PostgreSQL, SQLAlchemy/Alembic, Docker Compose, configuration validation, health endpoints, and test harnesses.
- **Detailed tasks:** Pin toolchain versions; structure backend/frontend packages; add migrations; configure lint/type/test/build commands; display a prominent paper-trading banner; enforce startup failure for unsafe configuration.
- **Tests and verification:** Backend and frontend smoke tests, migration upgrade/downgrade, container health checks, strict type checks, lint, and assertion that live-order execution is unavailable.
- **Acceptance criteria:** One documented local workflow starts healthy services; paper mode is the default; no strategy, broker authentication, or order code exists.
- **Dependencies:** Phase 0.
- **Risks:** Windows/Docker differences, dependency incompatibility, insecure configuration defaults.
- **Completion checklist:** [x] Services scaffolded; [x] database model and migration created; [x] checks automated and passing; [x] paper banner verified; [x] documentation updated; [x] `docker compose config` verified; [x] Docker images built; [x] live PostgreSQL migration and health verified; [x] backend health and system status verified; [x] frontend and safety banner verified in the running stack; [x] fail-closed live-order configuration verified; [x] container logs reviewed; [x] clean stack shutdown verified.

## Phase 2: Historical ingestion

**Status:** In progress (Phase 2A complete; Phase 2B repaired and awaiting re-verification)

- **Objective:** Produce validated, point-in-time historical spot, futures, option, and reference datasets.
- **Deliverables:** Canonical schemas, ingestion adapters, effective-dated instrument snapshots, market calendar, validators, provenance manifests, and data-quality reports.
- **Detailed tasks:** Define timestamps and identifiers; implement idempotent imports; detect gaps, duplicates, invalid quotes, and out-of-order events; document data licensing and retention.
- **Tests and verification:** Schema/contract tests, timezone and expiry cases, duplicate/idempotency tests, corrupt-input fixtures, and reproducible sample import.
- **Acceptance criteria:** A bounded licensed sample imports deterministically with lineage and explicit quality status.
- **Dependencies:** Phase 1 and lawful data access.
- **Risks:** Missing bid/ask history, token changes, incomplete contract metadata, rate limits, and licensing restrictions.
- **Phase 2B status and limitations:** Initial evidence verifies authentication and general candle/OI/FULL operations, but review found an internal SDK profile request and an over-broad NIFTY-family selector. Both are repaired offline. Nifty-specific claims require one new separately authorized bounded probe. No backtesting or performance conclusion is supported.
- **Completion checklist:** [x] Phase 2A foundation; [x] Phase 2B adapter and safety gates; [x] initial generic capability evidence reviewed; [x] login-only and exact Nifty selector repairs; [x] zero provider requests during repair; [ ] separately authorized repaired probe; [ ] lawful real-data sample ingested.

## Phase 3: Features and labels

**Status:** Pending

- **Objective:** Build versioned, point-in-time features and economically meaningful labels.
- **Deliverables:** Feature registry, label definitions, dataset builder, manifests/hashes, missing-data policy, and leakage guards.
- **Detailed tasks:** Implement underlying, option-chain, time, and regime features; define neutral-zone/triple-barrier/direct-option-return labels; record horizons, execution delay, and costs.
- **Tests and verification:** Timestamp boundary tests, same-bar execution safeguards, train-only transformation tests, deterministic rebuilds, and no-lookahead assertions.
- **Acceptance criteria:** Identical input/configuration produces identical datasets; every feature and label has availability and lineage metadata.
- **Dependencies:** Phase 2 and agreed cost/horizon policies.
- **Risks:** Look-ahead leakage, sparse contracts, survivorship bias, revised data, unstable labels.
- **Completion checklist:** [ ] Features versioned; [ ] labels versioned; [ ] leakage tests pass; [ ] dataset hash stable; [ ] limitations recorded.

## Phase 4: Baseline modeling

**Status:** Pending

- **Objective:** Evaluate `CALL`, `PUT`, and `NO_TRADE` decisions honestly against credible baselines.
- **Deliverables:** No-trade/random/rule/logistic/tree baselines, purged walk-forward splitter with embargo, calibration pipeline, experiment registry, and untouched holdout policy.
- **Detailed tasks:** Fit preprocessing inside folds; compare balanced classification and economic metrics; tune thresholds on validation periods only; record every experiment.
- **Tests and verification:** Split-overlap and embargo tests, repeatability checks, training-only preprocessing assertions, metric fixtures, and calibration checks.
- **Acceptance criteria:** Results are reported across chronological folds and costs, with no shuffled cross-validation and no final-holdout tuning.
- **Dependencies:** Phase 3.
- **Risks:** Overfitting, multiple testing, class imbalance, regime dependence, and misleading accuracy.
- **Completion checklist:** [ ] Baselines run; [ ] walk-forward verified; [ ] calibration assessed; [ ] holdout preserved; [ ] results documented.

## Phase 5: Options backtester

**Status:** Pending

- **Objective:** Simulate the full event sequence using tradeable option observations and realistic friction.
- **Deliverables:** Event clock, shared strategy/risk interfaces, contract selector, simulated broker, portfolio ledger, cost/fill models, and reproducible reports.
- **Detailed tasks:** Process events chronologically; buy at ask/sell at bid by default; apply latency, brokerage, taxes, slippage, quote freshness, partial/non-fill logic, and intraday exits.
- **Tests and verification:** Event-ordering tests, accounting invariants, fee fixtures, stale/missing quote cases, deterministic scenarios, and report-to-ledger reconciliation.
- **Acceptance criteria:** Every decision and P&L amount is traceable; final evaluation uses real option prices/quotes; Black–Scholes synthetic prices are never described as historical evidence.
- **Dependencies:** Phases 2–4 and adequate historical option observations.
- **Risks:** Optimistic fills, incomplete charges, stale quotes, and effective-date errors.
- **Completion checklist:** [ ] Event engine complete; [ ] risk integrated; [ ] costs effective-dated; [ ] accounting reconciled; [ ] assumptions disclosed.

## Phase 6: Dashboard

**Status:** Pending

- **Objective:** Provide trustworthy research, risk, and operational visibility.
- **Deliverables:** Overview, strategy, backtest, replay, trades, system, and safe-settings pages plus supporting APIs/event streams.
- **Detailed tasks:** Show signals/probabilities, rejected reasons, trades, positions, P&L, drawdown, health, freshness, versions, logs, reports, and a permanent paper-only banner.
- **Tests and verification:** API schema tests, component/accessibility checks, empty/error/loading states, Playwright workflows, and sensitive-data display tests.
- **Acceptance criteria:** Users can trace every simulated trade/rejection and reconcile dashboard metrics without exposure of secrets.
- **Dependencies:** Phases 1 and 5.
- **Risks:** Misleading aggregates, slow queries, inaccessible visuals, log leakage, ambiguous mode labels.
- **Completion checklist:** [ ] Required views built; [ ] metrics reconcile; [ ] banner verified; [ ] accessibility checked; [ ] redaction verified.

## Phase 7: Market replay

**Status:** Pending

- **Objective:** Exercise production-compatible paths against accelerated deterministic history.
- **Deliverables:** Replay session controller, chronological event stream, 1x/5x/20x/100x speeds, pause/resume/stop, recovery, and persisted session state.
- **Detailed tasks:** Share feature/strategy/risk/accounting/dashboard paths with paper mode; simulate session boundaries and square-off; support deterministic seeds and restart tests.
- **Tests and verification:** Ordering/no-future-access tests, speed independence, pause/resume/stop behavior, restart recovery, and equivalence with backtest semantics.
- **Acceptance criteria:** Repeating a session/configuration/seed produces the same decisions and ledger; future events are inaccessible.
- **Dependencies:** Phases 5–6.
- **Risks:** Async races, backpressure, nondeterminism, clock leakage.
- **Completion checklist:** [ ] Controls complete; [ ] ordering verified; [ ] deterministic rerun verified; [ ] restart tested; [ ] UI integrated.

## Phase 8: SmartAPI paper mode

**Status:** Pending

- **Objective:** Consume live SmartAPI market data while ensuring every execution remains simulated.
- **Deliverables:** Secure authentication/session handling, live feed adapter, bounded strike subscriptions, health/reconnect logic, paper broker, and end-of-day reconciliation.
- **Detailed tasks:** Load secrets outside Git; handle token expiry, stale/out-of-order quotes and subscription changes; simulate bid/ask fills; persist identical order/fill events; operate through Indian market hours.
- **Tests and verification:** Mocked authentication, disconnect/reconnect, rate-limit, stale-data, market-hours, restart, reconciliation, and order-endpoint-denial tests.
- **Acceptance criteria:** Complete paper sessions run without any live order API call; connection health and all simulated activity are observable.
- **Dependencies:** Phases 5–7, SmartAPI access, and secure local secret setup.
- **Risks:** API/feed changes, network loss, token expiry, clock skew, accidental endpoint exposure.
- **Completion checklist:** [ ] Live feed stable; [ ] paper fills verified; [ ] reconnect tested; [ ] reconciliation passes; [ ] real orders proven unreachable.

## Phase 9: Extended paper evaluation

**Status:** Pending

- **Objective:** Gather multi-regime forward-test evidence and validate long-running operations.
- **Deliverables:** Evaluation protocol, daily/weekly reports, drift and reliability metrics, incident log, soak results, and go/no-go evidence package.
- **Detailed tasks:** Run at least 8–12 weeks and 100 completed simulated trades, whichever takes longer; cover expiry/non-expiry, trend/range, volatility, gaps, outages, and restarts.
- **Tests and verification:** Long-run soak, data completeness, daily ledger reconciliation, recovery drills, alert/circuit-breaker tests, and regime/cost sensitivity analysis.
- **Acceptance criteria:** Predetermined evidence and reliability thresholds are met with no unresolved critical incidents; otherwise remain in paper mode and extend evaluation.
- **Dependencies:** Phase 8 and sufficient market sessions.
- **Risks:** Insufficient sample size, regime shifts, operational gaps, selection bias.
- **Completion checklist:** [ ] Minimum duration met; [ ] trade count met; [ ] regimes covered; [ ] incidents resolved; [ ] evidence reviewed.

## Phase 10: AWS paper deployment

**Status:** Pending

- **Objective:** Operate the proven system in AWS while remaining paper-only.
- **Deliverables:** Mumbai-region architecture, private database, encrypted secrets, backups, monitoring/alarms, static outbound IP readiness, deployment/rollback and recovery runbooks.
- **Detailed tasks:** Implement least-privilege IAM and private networking; deploy container services; centralize redacted logs; validate position-aware restarts; separate read-only views from controls.
- **Tests and verification:** Infrastructure policy/security checks, backup restore, failover/restart, paper soak, static egress confirmation, and live-order denial.
- **Acceptance criteria:** AWS paper mode is stable, observable, recoverable, and incapable of placing live orders.
- **Dependencies:** Phase 9, cloud budget, security review, and approved architecture.
- **Risks:** Cloud cost, secret/network misconfiguration, service failure, false confidence from deployment.
- **Completion checklist:** [ ] Infrastructure reviewed; [ ] backups restored; [ ] monitoring tested; [ ] paper soak complete; [ ] live orders remain disabled.

## Phase 11: Gated live option buying

**Status:** Pending

- **Objective:** Separately determine whether minimal-exposure live option buying can be authorized; this phase does not presume approval.
- **Deliverables:** Independent live adapter, broker reconciliation, layered build/runtime/account gates, static-IP order access, release-specific approval record, kill switches, and live incident runbook.
- **Detailed tasks:** Reconfirm broker/exchange/regulatory requirements; review Phase 9–10 evidence; restrict permissions and exposure; require manual release/account approval; prohibit naked selling and one-variable activation.
- **Tests and verification:** Independent security/risk review, sandbox/mock order-state tests, duplicate/idempotency tests, disconnect/reconciliation drills, kill-switch tests, and default-deny order endpoint tests.
- **Acceptance criteria:** Every blueprint gate is evidenced and explicitly approved for a specific release/account; absent approval, the platform remains paper-only. Option selling requires a separate project review.
- **Dependencies:** Successful Phases 0–10, current compliance review, explicit owner authorization, and broker approval.
- **Risks:** Financial loss, regulatory change, credential compromise, reconciliation failure, latency/network failure, tail risk.
- **Completion checklist:** [ ] Evidence independently reviewed; [ ] requirements current; [ ] layered gates verified; [ ] emergency controls drilled; [ ] explicit approval recorded—or [ ] live execution declined.
