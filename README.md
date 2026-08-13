# AlphaOption

AlphaOption is a local-first machine-learning research, backtesting, accelerated market-replay, and paper-trading platform for **Nifty 50 option buying**. It is designed to test a market hypothesis rigorously—not to promise that machine learning can predict markets or guarantee returns.

> **Safety status:** Live orders are disabled. The current project contains documentation only, uses a ₹20,000 virtual-capital assumption, and must default to `TRADING_MODE=paper` with `ENABLE_LIVE_ORDERS=false`.

## Research question

Can machine-learning models identify short-horizon Nifty 50 option-buying opportunities that produce persistent out-of-sample returns after bid–ask spreads, brokerage, taxes, slippage, latency, and account risk are included?

AlphaOption compares ML with transparent no-trade, momentum, mean-reversion, and statistical baselines. Classification accuracy is insufficient: evidence must remain economically meaningful across leakage-safe chronological walk-forward periods and conservative execution assumptions.

## Operating modes

| Mode | Data | Broker | Purpose | Real orders |
| --- | --- | --- | --- | --- |
| Backtest | Historical dataset | Simulated event broker | Research and evaluation | Never |
| Replay | Historical event stream | Simulated paper broker | Accelerated live-like validation | Never |
| Paper | Live SmartAPI feed, later | Paper broker | Forward testing | Never |
| Live | Live SmartAPI feed, future only | Separate future Angel One adapter | Explicitly gated deployment | Disabled initially |

Changing one setting must never be sufficient to enable live trading. The same feature, strategy, independent risk, portfolio, and event contracts are planned across modes, while broker and market-data behavior remain isolated behind adapters.

## Planned architecture and stack

Market data flows into an immutable raw-data layer, point-in-time feature and label pipelines, versioned models and strategy logic, an independent account-level risk engine, broker interfaces, portfolio accounting, FastAPI APIs/event streams, and a Next.js dashboard. PostgreSQL stores traceable research, trading-simulation, and operational records.

Planned technology:

- Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL
- Pandas/Polars, NumPy/SciPy, scikit-learn, LightGBM/XGBoost
- Next.js with TypeScript, Tailwind CSS, Recharts, accessible UI components
- Docker Compose, Pytest, Ruff, static typing, ESLint, Playwright, GitHub Actions
- Later only: AWS in/near India with private networking, managed secrets, monitoring, backups, and static outbound IP readiness

## Current status

**Phase 1 — Local application skeleton is complete.** The FastAPI, Next.js, PostgreSQL, Alembic, Docker Compose, health/status, dashboard-shell, and automated-check foundations have passed local and full-stack container verification. SmartAPI, market data, models, strategies, backtesting, brokers, trades, and order placement remain absent. Phase 2 has not started.

See:

- [`PROJECT_BLUEPRINT.md`](PROJECT_BLUEPRINT.md) — source-of-truth architecture and research design
- [`implementation_plan.md`](implementation_plan.md) — Phases 0–11 with gates and checklists
- [`PROJECT_UPDATE.md`](PROJECT_UPDATE.md) — living status and progress history
- [`SECURITY.md`](SECURITY.md) — secret handling and paper/live isolation

## Local-development roadmap

1. Repository foundation
2. Local application skeleton
3. Historical ingestion
4. Features and labels
5. Baseline modeling
6. Event-driven options backtester
7. Dashboard
8. Historical market replay
9. SmartAPI live-data paper mode
10. Extended paper evaluation
11. AWS paper deployment
12. Separately reviewed, gated live option buying

## Local startup and operations

Prerequisites are Docker Desktop with Linux containers enabled and Docker Compose. A real `.env` is optional because Compose supplies safe local defaults; if one is created, copy `.env.example`, keep it untracked, and never add real broker credentials during Phase 1.

Build and start the complete stack:

```powershell
docker compose up --build -d
```

The backend automatically applies `alembic upgrade head` before starting. To apply or inspect migrations explicitly:

```powershell
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic current
```

Open:

- Dashboard: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/health>
- System status: <http://localhost:8000/api/system/status>

Run backend checks with an installed Python 3.12 and `uv`:

```powershell
cd backend
uv sync --python 3.12 --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic upgrade head --sql
```

Run frontend checks:

```powershell
cd frontend
npm install
npm test
npm run lint
npm run typecheck
npm run build
npm audit
```

Inspect and stop the stack cleanly:

```powershell
docker compose ps
docker compose logs --no-log-prefix backend frontend
docker compose down
```

Use `docker compose down -v` only when intentionally deleting local PostgreSQL data. PostgreSQL has no host port; the backend and frontend bind only to localhost. The first AWS deployment must remain paper-only.

## Research and execution integrity

- Final option-strategy evaluation uses real historical option prices or quotes where available, with bid/ask spread, brokerage, statutory costs, latency, liquidity, and slippage.
- Black–Scholes may support theoretical checks, Greeks, or IV inversion from observed prices; synthetic premiums are not historical-market evidence.
- Validation is chronological walk-forward with purging and embargo. Shuffled cross-validation is prohibited.
- Every simulated trade requires independent account-level risk approval, and every rejection must be recorded and explainable.

## Safety disclaimer

AlphaOption is an educational and research project, not financial advice. Backtests and paper results do not guarantee future performance. Options can lose value rapidly, including the entire premium paid. Any future live option buying requires independent technical, security, risk, broker, regulatory, and owner approval. Live option selling is outside the approved scope.
