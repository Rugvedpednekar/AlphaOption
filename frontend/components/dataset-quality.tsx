"use client";

import { useEffect, useState } from "react";
import {
  fetchBackfillRuns,
  fetchDatasetQuality,
  fetchMarketDataCoverage,
  type BackfillRun,
  type DatasetQuality as Quality,
} from "@/lib/api";

export function DatasetQuality() {
  const [quality, setQuality] = useState<Quality | null>(null);
  const [runs, setRuns] = useState<BackfillRun[]>([]);
  const [state, setState] = useState<"loading" | "empty" | "ready" | "error">("loading");
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchMarketDataCoverage(controller.signal), fetchBackfillRuns(controller.signal)])
      .then(async ([coverage, backfills]) => {
        setRuns(backfills.items);
        const candidate = coverage.coverage.find((item) => item.timeframe === "5m");
        if (!candidate) return setState("empty");
        setQuality(await fetchDatasetQuality(candidate.instrument_id, controller.signal));
        setState("ready");
      })
      .catch(() => setState("error"));
    return () => controller.abort();
  }, []);
  if (state === "loading") return <p role="status">Loading dataset quality…</p>;
  if (state === "error") return <div role="alert">Dataset quality is unavailable.</div>;
  if (state === "empty" || !quality) return <section><h2>Dataset Quality</h2><p>No five-minute dataset is available for assessment.</p></section>;
  const syntheticOnly = quality.synthetic_count > 0 && quality.genuine_count === 0;
  return <section>
    {syntheticOnly && <div role="alert"><strong>SYNTHETIC-ONLY DATASET</strong> — unsuitable for genuine-market or performance conclusions.</div>}
    <h2>Observed coverage</h2>
    <p>{quality.observed_start ? new Date(quality.observed_start).toLocaleString() : "Unavailable"} through {quality.observed_end ? new Date(quality.observed_end).toLocaleString() : "Unavailable"}</p>
    <dl>
      <dt>Candles / observed dates</dt><dd>{quality.total_candles} / {quality.observed_trading_dates}</dd>
      <dt>Genuine / synthetic</dt><dd>{quality.genuine_count} / {quality.synthetic_count}</dd>
      <dt>Complete / partial / non-regular sessions</dt><dd>{quality.complete_sessions} / {quality.partial_sessions} / {quality.non_regular_sessions}</dd>
      <dt>Internal raw gaps</dt><dd>{quality.internal_five_minute_gap_count}</dd>
      <dt>ML readiness</dt><dd>{quality.ml_readiness.replaceAll("_", " ")}</dd>
      <dt>Latest backfill</dt><dd>{runs[0]?.status ?? "No backfill run"}</dd>
    </dl>
    <h3>Monthly coverage</h3>
    {quality.monthly.length ? <ul>{quality.monthly.map((month) => <li key={month.month}>{month.month}: {month.candles} candles, {month.complete_sessions} complete, {month.partial_sessions} partial observed sessions</li>)}</ul> : <p>No monthly observations.</p>}
    <p><strong>Regular-session structural assumption:</strong> {quality.regular_session_assumption}. Dates with zero rows are not classified as missing sessions or holidays.</p>
    <p><strong>Licensing and retention:</strong> Provider access does not establish storage, licensing, or redistribution rights.</p>
    <p>This aggregate status does not prove predictability or profitability. No prices, quantities, predictions, accuracy, trades, or P&amp;L are displayed.</p>
  </section>;
}
