# Phase 3 Feature Engineering

## Scope and architecture

Phase 3 transforms one registered instrument's completed `FIVE_MINUTE` candles into a
versioned, point-in-time feature table. It reads `market_candles` without changing them,
writes run audits to `feature_runs`, and writes normalized numeric columns to
`market_features`. Model inputs and experimental targets have distinct columns and API
objects. No provider, model, backtest, signal, or order path is involved.

A candle timestamp denotes the start of its five-minute interval. Its row becomes eligible
only after the interval closes. Requests use explicit, half-open UTC bounds `[from, to)` and
are processed chronologically for one instrument and interval. Missing prices are never
interpolated. Duplicate timestamps, invalid OHLCV, mixed genuine/synthetic sources, and
non-finite values fail closed.

## Model-input features

All inputs at time `t` use candle `t` or older candles only.

- Returns: simple and log close returns over 1, 3, and 6 bars.
- Candle shape: `(high-low)/close`, `(close-open)/open`, upper and lower wick divided by
  close, and `(open-previous_close)/previous_close`.
- Trend: EMA 9 and EMA 21, their close-normalized spread, close distance from each EMA,
  and one-bar EMA slopes. Each EMA is seeded with its period's simple mean.
- Momentum: RSI 14 using Wilder's initial mean gain/loss and recursive smoothing. A flat
  window is 50; a gain-only window is 100.
- Volatility: true range, Wilder ATR 14, ATR/close, and population standard deviation of
  one-bar log returns over 12 and 36 observations.
- Volume: percent change, 20-bar population mean and standard deviation, and z-score.
  When both adjacent volumes are zero, percent change is zero. A zero-variance 20-bar
  window yields a zero z-score, not infinity or a fabricated directional signal.
- Session: Asia/Kolkata weekday, minutes since 09:15, intraday sine/cosine over the
  375-minute session, and first/last 30-minute flags. Candles outside 09:15–15:30 fail.

Warm-up values remain null. A row is marked usable only when every model input is
available; the longest lookback requires 36 prior one-bar returns. Zero prices are rejected
where ratios or returns would be undefined; zero volume is valid.

## Targets

Targets are research labels, never model inputs:

- `future_return_15m = close(t+3) / close(t) - 1`
- `future_return_30m = close(t+6) / close(t) - 1`
- `direction_15m` and `direction_30m`: `up`, `down`, or `neutral`
- stored threshold: `max(0.001, 0.5 * ATR14(t) / close(t))`

`up` is strictly above the threshold, `down` strictly below its negative, and boundary
values are neutral. A target is unavailable if its complete horizon is absent, contains a
raw five-minute gap, or crosses an Asia/Kolkata trading date. The builder never reaches
outside the requested dataset to fill a target. The final three and six rows therefore lack
their respective outcomes. This experimental target choice is not evidence of predictive
power or profitability.

## Persistence and reproducibility

Alembic revision `20260813_0004` adds normalized `feature_runs` and `market_features`
tables. Rows are unique by instrument, interval, candle timestamp, and feature version.
The feature definition and public version form a deterministic SHA-256 configuration hash.
Reusing a version with another definition fails rather than overwriting data. Reruns skip
existing rows. A failed write is rolled back before its sanitized failure audit is committed
separately. Core values are columns rather than JSON blobs.

Source classification is copied from the eligible candle set and exposed as `genuine` or
`synthetic`. Mixed sets are rejected. Synthetic/fixture results cannot support model,
backtest, trading, or performance conclusions.

## Interfaces and safeguards

`alphaoption-features build` requires an instrument UUID, `FIVE_MINUTE`, explicit UTC
bounds, a feature version, and exactly one of `--dry-run` or `--execute`. Dry-run reads only
eligibility metadata and reports aggregate counts, warm-up, target tails, source, and hash;
it performs no writes or network calls.

Read-only `/api/features` routes provide bounded run summaries, coverage, null counts,
target distributions, and a paginated preview. Preview responses nest `model_inputs` and
`targets` separately and never expose entire datasets, credentials, provider payloads, or
raw errors. The Feature Status dashboard repeats the leakage and synthetic-data warnings.

## Known limitations

- Only one registered instrument and `FIVE_MINUTE` interval are supported per build.
- Session conversion uses fixed exchange hours; an exchange holiday/calendar service is
  not yet integrated.
- Raw gaps are barriers, not assertions that a market candle is missing.
- Corporate/index methodology revisions and provider corrections are not modeled.
- No ML model, feature selection, backtest, option-chain feature, Greek, PCR, synthetic
  option, signal, P&L, or profitability result exists in Phase 3.
