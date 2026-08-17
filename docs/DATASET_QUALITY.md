# Phase 4 Dataset Quality

Phase 4 assesses stored Nifty 50 spot `FIVE_MINUTE` candles without exposing or
manufacturing prices or quantities. The service reports aggregate requested and observed
bounds, source counts, structural validity, observed-date sessions, internal gaps, monthly
coverage, volume-null/zero counts, and longest contiguous sequences. Genuine and synthetic
data remain explicitly separated.

## Structural session assumption

The deterministic structural assumption is Asia/Kolkata 09:15 through 15:30, with candle
starts from 09:15 through 15:25. Exactly 75 distinct five-minute starts constitute a
regular complete observed session. Other observed dates are partial or non-regular. This
is not an official exchange calendar: dates with zero rows are not declared missing
sessions or holidays, and special sessions may be classified as non-regular. No value is
interpolated, forward-filled, or manufactured.

## Conservative ML-readiness categories

- Fewer than 250 complete observed sessions: `insufficient`.
- 250–499: `limited_research_dataset`.
- At least 500 across multiple years: `potentially_suitable_for_initial_walk_forward_experiments`.

The higher categories additionally require no duplicate keys, invalid OHLCV, or non-finite
values and require genuine/synthetic separation. They do not prove predictability or
profitability and do not authorize modeling or backtesting.

## Access and limitations

Bounded read-only APIs provide aggregate quality and backfill-run summaries. The Dataset
Quality dashboard displays coverage, monthly/session counts, source separation, raw gaps,
latest backfill state, and warnings. Provider access does not establish storage, licensing,
or redistribution rights. Genuine candles, database state, raw evidence, prices, and
quantities must never be committed.

## Observed local aggregate — 2026-08-16

The single authorized backfill produced 85,446 genuine candles across 1,145 observed
dates, from `2022-01-03T03:45:00Z` through `2026-08-14T04:25:00Z`. Structural assessment
found 1,128 complete regular sessions, 14 partial regular sessions, 3 non-regular observed
sessions, 16 internal five-minute gaps, and a longest contiguous sequence of 75. Duplicate
keys, invalid OHLCV, non-finite values, out-of-order rows, and null volumes were all zero;
all 85,446 volume observations were zero. Raw zero volume is preserved, but volume-derived
features are unavailable and uninformative for this historical index dataset unless a future
genuine source supplies nonzero volume.

The 30-day chunk audits do not support a 1,500-row response ceiling. Nine chunks returned
exactly 1,500 rows, but 29 chunks exceeded 1,500 and the maximum response contained 1,725
rows. None of the 16 internal gaps aligned with a chunk boundary. No corrective provider run
or chunking change was justified by this aggregate evidence.

Monthly coverage spans 56 monthly buckets from January 2022 through August 2026. Months
containing partial or non-regular observations were October 2022, November 2023, March,
May, July and November 2024, October 2025, and August 2026. The aggregate readiness label
is `potentially_suitable_for_initial_walk_forward_experiments`; this classification applies
only to dataset size and coverage, not feature readiness, predictability, execution realism,
or profitability. Expanded feature generation failed closed because the three non-regular
observed sessions require an explicit policy. Zero-row dates are not interpreted as holidays
or missing sessions. Licensing, storage, and redistribution rights remain unresolved.
