# AlphaOption Project Update

**Last updated:** 2026-08-16

## Project status

Historical data expansion and dataset-quality work is runtime-verified. Phases 0–3 are complete and the Phase 4 authorized backfill completed. Model, backtest, and performance conclusions remain out of scope.

## Current phase

**Phase 4 — Historical expansion and dataset quality: Runtime verified**

Phases 0–3 are completed; Phase 4 is in progress; later modeling and trading phases are pending. `TRADING_MODE=paper` and `ENABLE_LIVE_ORDERS=false` remain enforced safe defaults.

## Completed work

- `PROJECT_BLUEPRINT.md` completed with architecture, research methodology, operating modes, safety gates, Phases 0–11, and success criteria.
- Initial Git repository and `main` branch established.
- Phase 0 supporting documentation drafted and aligned to the blueprint.
- Blueprint encoding normalized for reliable Windows and UTF-8 rendering.

- Phase 0 documentation foundation verified, committed, and pushed.
- FastAPI application with safe Pydantic settings, local CORS, structured redacted logging, and read-only health/status routes.
- SQLAlchemy PostgreSQL configuration, `system_events` model, Alembic environment, and initial migration.
- Next.js 16/TypeScript strict dashboard shell with accessible navigation, health integration, safe empty states, and paper-only banner.
- Docker Compose definitions for private PostgreSQL networking, backend, and frontend with health dependencies and named storage.
- Backend and frontend automated checks plus locked Python/npm dependencies.
- Phase 2A source decision and complete market-data dictionary.
- Canonical `instruments`, `market_candles`, and `ingestion_runs` models plus Alembic revision `20260813_0002`.
- Provider protocol, deterministic synthetic fixture, UTC normalization, validation, idempotent writes, conflict rejection, audit records, and CLI.
- Bounded read-only coverage, instrument, candle, and ingestion-run APIs.
- Data Status UI with loading, empty, error, coverage, audit, and unmistakable synthetic-data states.
- Phase 2B isolated read-only SmartAPI adapter, deterministic bounded probe, protected settings, redacted ignored evidence writer, and explicit execution acknowledgement.
- Zero-network dry run and mocked safety tests covering fail-closed configuration, call bounds, session termination, deterministic selection, and secret leakage.
- One bounded credentialed probe: authentication and logout verified; current Nifty spot/future/CE/PE discovery, candle OHLC/volume, derivative historical OI, and current FULL snapshot/depth field categories observed.

## Verification performed

- Read `PROJECT_BLUEPRINT.md` completely before supporting-document edits.
- Compared phase names and boundaries across the blueprint and implementation plan.
- Reviewed paper/live safety language and configuration defaults.
- `docker compose config` completed successfully.
- Backend Ruff lint and format checks completed successfully on Python 3.12.13.
- Backend Pytest completed: 6 passed (with a third-party TestClient deprecation warning and sandbox cache warning).
- Alembic offline PostgreSQL migration SQL generation completed successfully.
- Host-started backend endpoints returned safe paper-mode data and correctly reported the absent local PostgreSQL service as unhealthy/degraded.
- Frontend component tests completed: 4 passed, covering the safety banner and healthy, unavailable, and database-unhealthy states.
- Frontend ESLint, strict TypeScript check, and Next.js production build completed successfully.
- Host-started production frontend returned HTTP 200 and rendered both AlphaOption branding and the exact paper-only banner.
- Full `npm audit` completed with 0 vulnerabilities after upgrading to Next.js 16.3 and Recharts 3.
- Docker images built and the full Compose stack started successfully.
- PostgreSQL, backend, and frontend container health checks completed successfully.
- PostgreSQL remained internal to the Compose network with no published host port.
- Alembic's current revision was checked against the running PostgreSQL database.
- Backend health and system-status responses were checked in the running stack.
- The dashboard loaded and displayed the exact `PAPER TRADING — NO REAL ORDERS` safety banner.
- Startup with `ENABLE_LIVE_ORDERS=true` was checked and failed closed as required.
- Container logs were reviewed, and the stack was shut down cleanly.
- The frontend container health check was corrected from IPv6-resolving `localhost` to `127.0.0.1`.
- The frontend package lock was regenerated with Linux-compatible optional dependencies.
- Phase 2A backend Pytest: 14 passed; third-party TestClient deprecation and sandbox Pytest-cache warnings remain.
- Ruff lint and format checks passed for 28 Python files.
- Alembic offline SQL generation passed through `20260813_0002`.
- Frontend Vitest: 5 passed; ESLint, strict TypeScript, Next.js production build, and npm audit (0 vulnerabilities) passed.
- `docker compose config --quiet` passed; Docker images built successfully.
- Live PostgreSQL migration reported `20260813_0002 (head)`.
- First synthetic fixture run: 8 received, 8 inserted, 0 updated/rejected. Second run: 8 received, 0 inserted/updated/rejected.
- Live coverage API reported 4 instruments and 4 candles (spot 1, future 1, option 2), all clearly synthetic.
- Browser verification confirmed Data Status, the exact paper-only banner, synthetic warning, coverage, and two ingestion audits.
- All three containers reached healthy; PostgreSQL exposed no host port. Current logs showed successful health/status/coverage requests.
- Container `ENABLE_LIVE_ORDERS=true` check exited 1 with the expected safety validation error.
- `docker compose down` removed all containers/network; post-shutdown `docker compose ps -a` was empty.
- Phase 2B backend Pytest: 25 passed with the existing third-party TestClient deprecation warning.
- Ruff lint and format checks passed for 39 Python files; the official SmartAPI SDK imported successfully from the locked environment.
- Alembic offline SQL generation passed through `20260813_0002`; the backend wheel built successfully.
- Frontend Vitest: 5 passed; ESLint, strict TypeScript, Next.js production build, and npm audit (0 vulnerabilities) passed.
- `docker compose config --quiet`, `git diff --check`, forbidden endpoint-string scanning, high-confidence secret scanning, and sensitive-filename scanning passed.
- A prospective tracked-only Git archive imported the SmartAPI package, passed all 25 backend tests, and built the backend wheel without ignored/runtime paths.
- `alphaoption-smartapi probe --dry-run` completed with zero network calls, SmartAPI disabled, live orders disabled, and read-only acknowledgement absent.

## Current blockers

- Phase 2 will require lawful access to historical option prices/quotes and confirmed data retention/licensing terms.
- SmartAPI capabilities, especially expired-option candles, remain unverified until an authorized Phase 2B credential test.
- The repository fixture is synthetic, is unsuitable for performance conclusions, and cannot validate provider completeness or execution realism.
- Phase 8 will require user-provided SmartAPI credentials stored outside source control; credentials are neither needed nor permitted in Phase 0.
- Live execution remains blocked by design until all Phase 11 gates and explicit approvals are satisfied.
- Expired-contract discovery, historical bid/ask, maximum provider retention, and licensing/redistribution rights remain unresolved.

## Major technical decisions

- Develop and verify locally on Windows/Docker Desktop before AWS.
- Use ₹20,000 virtual starting capital; simulate all initial trades.
- Support Nifty 50 option buying only; no naked or live option selling.
- Begin with backtest, accelerated replay, and live-data paper modes.
- Use one point-in-time strategy and independent account-level risk engine across modes.
- Isolate simulated/paper and future live broker adapters.
- Model `CALL`, `PUT`, and `NO_TRADE`; never force a trade.
- Use chronological walk-forward validation with purging/embargo; prohibit shuffled cross-validation.
- Require actual option observations and conservative spreads, costs, latency, and slippage for final economic evaluation.
- Never present Black–Scholes synthetic premiums as historical option-market evidence.
- Keep the first AWS deployment paper-only; require a static outbound IP only for future approved SmartAPI order APIs.

## Next actions

1. Review the uncommitted Phase 4 implementation and observed aggregate evidence.
2. Resolve how non-regular observed sessions should be handled before any expanded Phase 3 feature rebuild; do not change existing formulas or eligibility policy implicitly.
3. Resolve provider/exchange licensing, retention, and redistribution questions; do not begin ML, backtesting, or trading capability.

### 2026-08-16 — Phase 4 implementation; provider gate blocked

- Added exact-spot, five-minute-only resumable backfill planning and execution with 30-day chunks, a 60-request cap, durable chunk/run audits, no retries, per-chunk commits, observed-empty classification, and unconditional provider cleanup.
- Added aggregate dataset-quality/readiness analysis, bounded APIs, and Dataset Quality dashboard states without exposing individual prices or quantities.
- Added Alembic revision `20260813_0005` because existing ingestion audits do not store chunk bounds required for safe resume and covered-chunk skipping.
- Focused fixture tests passed. The mandatory Compose gate could not start because the Docker Desktop Linux engine was unavailable; therefore database migration/connectivity, fixture execution, dry-run, and the authorized credentialed backfill were not attempted. SmartAPI calls remained zero and `.env` remained unchanged with `SMARTAPI_ENABLED=false`.

### 2026-08-16 — Phase 4 runtime verification and authorized backfill completed

- Diagnosed the PostgreSQL authentication mismatch as an automatically loaded `.env` placeholder overriding unchanged `main` Compose fallbacks. Using an empty ignored interpolation file restored the established database semantics; no role, password, database, schema, table, or volume state changed.
- Preserved the original named volume and verified aggregate counts before and after the reversible `20260813_0005 → 20260813_0004 → 20260813_0005` migration cycle. PostgreSQL remained internal-only and the full stack became healthy.
- Runtime fixture verification inserted 12 rows once, inserted zero on repeat, skipped the covered chunk, classified one empty chunk, and preserved one successful chunk before a sanitized synthetic failure.
- The authorized genuine run completed 57 sequential chunks with one authentication, 57 historical calls, one logout, and confirmed termination. It received 85,446 rows, inserted 84,022, recognized 1,424 duplicates, and rejected zero; accounting invariants passed.
- Quality assessment found 1,145 observed dates, 1,128 complete regular sessions, 14 partial sessions, 3 non-regular sessions, 16 internal gaps, and no duplicate keys, invalid OHLCV, non-finite, or out-of-order rows. Readiness is only potentially suitable for initial walk-forward experiments, not evidence of predictability or profitability.
- Aggregate chunk-audit analysis found nine responses with exactly 1,500 rows, while 29 exceeded 1,500 and the maximum was 1,725; none of the 16 internal gaps aligned with chunk boundaries, so no evidence supports a 1,500-row response ceiling and no corrective provider run was made.
- All 85,446 genuine historical index volume values are zero. Raw values remain unchanged, but volume-derived features are unavailable for this dataset. The size/coverage readiness label does not imply feature readiness, predictability, or profitability; licensing, storage, and redistribution rights remain unresolved.
- The optional expanded feature build failed closed with `outside-market-session` because of the non-regular observations. It wrote zero expanded feature rows, preserved the source-candle fingerprint, and was not retried. `SMARTAPI_ENABLED=false` was restored.

### 2026-08-13 — Phase 3 leakage-safe feature engineering completed

- Added normalized feature-run and feature-row persistence through proposed Alembic revision `20260813_0004`, including deterministic configuration hashes and separate model-input and target columns.
- Added completed-candle eligibility, strict source separation, transparent returns/EMA/Wilder RSI/Wilder ATR/volatility/volume/session features, null warm-up policy, and explicit no-future-input regression coverage.
- Added experimental 15/30-minute targets with a point-in-time ATR threshold, gap/session barriers, null tails, and no profitability claim.
- Added a repeat-safe CLI, bounded read-only APIs, a Feature Status dashboard, and detailed formula/timing documentation. No provider request, model, backtest, signal, or execution path was added.
- Verified Alembic upgrade/downgrade/re-upgrade through `20260813_0004`. Against the existing genuine local sample, dry-run found 1,424 eligible candles with zero writes; the first build created 1,424 feature rows and the repeat created zero while skipping all 1,424 existing rows. The source-candle fingerprint remained unchanged.
- Aggregate verification found 1,388 usable rows, 36 warm-up rows, 1,343 available 15-minute targets, and 1,283 available 30-minute targets. Null target counts include session/gap barriers as well as the final target tails. All five bounded feature APIs and the live dashboard responded successfully. These are previously observed local aggregate counts; the final review did not independently reproduce them because genuine candles are intentionally not stored in Git.

The repair made zero provider requests, did not modify ignored credentials or evidence, and did not start Phase 2C.

### 2026-08-13 — Phase 2D bounded historical verification completed

- Authorized one bounded spot-index `FIVE_MINUTE` ingestion covering 28 calendar days through the latest completed Indian market session. The dry-run produced one deterministic chunk with zero provider calls and zero database writes; fixture execution and repeat idempotency passed first.
- Added minimal lazy authentication and safe aggregate lifecycle reporting so authentication failures occur inside ingestion auditing and request/session totals can be reported without exposing protected data.
- Diagnosed an earlier zero-provider failure: whole-file injection supplied a host-loopback database address inside a container. The repaired execution retains Compose service DNS and injects only named SmartAPI variables; PostgreSQL remains internal.
- The newly authorized execution completed with one authentication attempt, one historical request, and logout. It received and inserted 1,424 rows with zero duplicates or rejections; UTC bounds, OHLCV validity, uniqueness, range containment, and accounting passed. Coverage responses no longer expose full symbols.
- Restored `SMARTAPI_ENABLED=false`. This single ingestion establishes neither maximum retention nor futures, options, expired-contract, licensing, redistribution, backtesting, ML, or profitability conclusions. Genuine local data must not be committed.

### 2026-08-13 — Phase 2C historical ingestion started

- Merged the reviewed Phase 2B repair and synchronized `main`.
- Added provider-independent UTC validation, deterministic chunking, fixture history, idempotent/conflict-aware storage, sanitized run audits, a gated SmartAPI historical adapter, CLI previews, bounded coverage/gap APIs, and historical Data Status states.
- Reused the Phase 2A tables. Added only backward-compatible revision `20260813_0003` for the genuinely required ingestion duplicate audit count; no redundant market-data table was created. Verification uses fixtures and mocks only; provider requests, orders, and WebSockets remain zero.
- Passed 65 backend tests, Ruff lint/format, offline Alembic generation, backend wheel builds (including a tracked-only export), 8 frontend tests, ESLint, strict TypeScript, Next.js production build, npm audit, Compose validation, diff and safety scans.
- Verified an isolated healthy Compose stack at Alembic head. Fixture history inserted records once and inserted zero on an identical repeat; bounded coverage/run/gap APIs and the live Data Status view showed sanitized synthetic results. Logs were reviewed and the stack plus its test-only volume shut down cleanly.

## Dated progress history

### 2026-08-13 — Expanded blueprint completed

- Completed `PROJECT_BLUEPRINT.md` as the architectural and research source of truth.
- Defined operating modes, event-driven evaluation, risk controls, dashboard, security, AWS paper deployment, and the separately gated Phase 11 live option-buying review.
- Corrected Windows-visible encoding corruption while preserving blueprint content.

### 2026-08-13 — Phase 0 documentation in progress

- Began aligning the implementation plan, progress log, README, ignore rules, safe environment template, and security policy with the completed blueprint.
- Kept all implementation work and credentials out of scope.

### 2026-08-13 — Phase 1 local application skeleton

- Marked Phase 0 completed and implemented the backend, database/migration, frontend dashboard, Docker Compose, and automated-check foundations.
- Chose synchronous SQLAlchemy/psycopg for the minimal health path, Next.js 16 with static standalone output, localhost-only host ports, and no PostgreSQL host port.
- Added no Redis because Phase 1 has no job coordination or transient live state requiring it.
- Initially kept Phase 1 in progress because Docker Desktop was installed but its Linux engine was not running during the first verification pass.

### 2026-08-13 — Phase 1 container acceptance completed

- Built and ran the complete PostgreSQL, FastAPI, and Next.js Docker Compose stack.
- Verified the applied Alembic revision, backend health/status responses, PostgreSQL health and network isolation, dashboard safety banner, fail-closed live-order configuration, container logs, and clean shutdown.
- Corrected the frontend health check to use IPv4 loopback and regenerated the frontend package lock for Linux container compatibility.
- Marked Phase 1 completed. Phase 2 remains pending.

### 2026-08-13 — Phase 2A market-data foundation completed

- Created a provider-independent canonical schema, provider protocol, validation/idempotency services, synthetic fixture CLI, bounded read APIs, and Data Status dashboard.
- Verified migration revision `20260813_0002`, repeat ingestion idempotency, live API/UI coverage, synthetic labeling, fail-closed safety, container logs, and clean shutdown.
- Kept SmartAPI and all real credentials out of the implementation. Phase 2 remains in progress pending Phase 2B provider capability validation.

### 2026-08-13 — Phase 2B capability probe implementation in progress

- Added a backend-only, read-only SmartAPI adapter and bounded CLI with explicit enablement and acknowledgement gates.
- Pinned the official SDK and minimum import/TOTP dependencies, suppressed SDK logging side channels, and kept session tokens memory-only.
- Passed the zero-network dry run and mocked safety suite. One explicitly acknowledged execution attempt stopped safely before provider contact with zero requests and no session. The ignored evidence passed leakage checks, and SmartAPI was disabled again.

### 2026-08-13 — Phase 2B bounded capability probe completed

- Revalidated protected local configuration, zero-network dry-run behavior, adapter isolation, and forbidden-operation scans.
- Completed one authenticated, sequential, read-only 14-request probe and verified session termination with no orders or restricted account operations.
- Verified current Nifty role discovery, bounded spot/future/CE/PE candles with OHLC and volume, live-contract historical OI, and current FULL snapshot/depth field categories.
- Kept expired contracts and historical bid/ask not-testable, passed evidence leakage scans, and restored SmartAPI to disabled.

### 2026-08-13 — Phase 2B review repair

- Found that pinned SDK `generateSession()` internally retrieved profile data and that the original selector admitted other NIFTY-family products.
- Replaced the helper with a guarded login-only SDK path and restricted selection to exact Nifty 50/NIFTY identities with expiry alignment.
- Downgraded Nifty-specific claims because generic-role evidence cannot retroactively prove derivative identity. No provider request was made; a new probe requires separate authorization.
