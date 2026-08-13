# AlphaOption

AlphaOption is a local-first machine-learning research, backtesting, accelerated market-replay, and paper-trading platform for **Nifty 50 option buying**. It is intended to test whether leakage-safe models and realistic execution assumptions can produce robust option-buying signals. Development and verification happen locally before any AWS deployment.

> [!WARNING]
> AlphaOption does not place live orders. Early trades are simulated with an initial-capital assumption of **₹20,000**. `ENABLE_LIVE_ORDERS` must remain `false` throughout the current phases.

## Initial scope

- Instruments: Nifty 50 options; buying only.
- Decisions: `CALL`, `PUT`, or `NO_TRADE`.
- Modes: historical backtesting, accelerated market replay, and live paper trading.
- Market data: historical files initially; Angel One SmartAPI historical/live data later.
- Shared logic: one strategy and account-level risk engine across every mode.
- Execution: separate paper broker and future live broker adapters. Live option selling is out of scope.

## Planned stack

Python 3.12, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pandas/Polars, scikit-learn, LightGBM/XGBoost, Next.js with TypeScript, Tailwind CSS, Recharts, Docker Compose, Pytest, and Playwright.

## Planned directory map

The directories below are architectural intent only; code is deliberately not scaffolded in Phase 0.

```text
AlphaOption/
├── backend/                 # FastAPI application and shared domain logic
│   ├── app/{api,domain,services,adapters}/
│   ├── migrations/
│   └── tests/
├── frontend/                # Next.js dashboard
├── data/{raw,interim,processed}/   # Local, ignored market data
├── artifacts/{models,reports}/     # Local, ignored outputs
├── infra/                   # Docker Compose and later AWS definitions
├── PROJECT_BLUEPRINT.md
├── implementation_plan.md
├── PROJECT_UPDATE.md
├── SECURITY.md
└── .env.example
```

## Documentation

- [Project blueprint](PROJECT_BLUEPRINT.md): architecture, research methodology, safety, and reproducibility.
- [Implementation plan](implementation_plan.md): milestone-by-milestone delivery plan.
- [Project update](PROJECT_UPDATE.md): current state and dated progress history.
- [Security policy](SECURITY.md): credential and paper/live isolation requirements.

## Getting started

Phase 0 contains documentation only. Copy `.env.example` to `.env` when local services are introduced, keep all values local, and never commit credentials or TOTP secrets. The next milestone is Phase 1: create the local backend/frontend skeleton and automated checks.

This software is for research and engineering evaluation, not financial advice. Simulated performance does not guarantee live results.
