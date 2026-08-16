"use client";

import { useEffect, useState } from "react";
import {
  fetchFeatureAvailability,
  fetchFeatureCoverage,
  fetchFeatureRuns,
  fetchTargetDistribution,
  type FeatureAvailability,
  type FeatureCoverageItem,
  type FeatureRun,
  type TargetDistribution,
} from "@/lib/api";

export function FeatureStatus() {
  const [coverage, setCoverage] = useState<FeatureCoverageItem[]>([]);
  const [runs, setRuns] = useState<FeatureRun[]>([]);
  const [availability, setAvailability] = useState<FeatureAvailability | null>(null);
  const [distribution, setDistribution] = useState<TargetDistribution | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchFeatureCoverage(controller.signal), fetchFeatureRuns(controller.signal)])
      .then(async ([coverageResult, runResult]) => {
        setCoverage(coverageResult.items);
        setRuns(runResult.items);
        const first = coverageResult.items[0];
        if (first) {
          const [available, targets] = await Promise.all([
            fetchFeatureAvailability(first.instrument_id, first.feature_version, controller.signal),
            fetchTargetDistribution(first.instrument_id, first.feature_version, controller.signal),
          ]);
          setAvailability(available);
          setDistribution(targets);
        }
        setState("ready");
      })
      .catch(() => setState("error"));
    return () => controller.abort();
  }, []);

  if (state === "loading") return <p role="status">Loading feature status…</p>;
  if (state === "error") return <div role="alert">Feature status is unavailable.</div>;
  if (!coverage.length) return <section><h2>Feature Status</h2><p>No feature rows have been built.</p><p>No ML model or backtest exists yet.</p></section>;
  const item = coverage[0];
  const run = runs[0];
  const nullCount = availability ? Object.values(availability.model_input_null_counts).reduce((sum, value) => sum + value, 0) : 0;
  return <section>
    {item.source_classification === "synthetic" && <div role="alert"><strong>SYNTHETIC FEATURE DATA</strong> — unsuitable for performance conclusions.</div>}
    <h2>Feature Status</h2>
    <p>Each model input uses completed candles at or before its timestamp. Targets are stored separately and may use bounded future candles.</p>
    <p><strong>No ML model or backtest exists yet.</strong> No predictions, signals, accuracy, P&amp;L, or profitability are reported.</p>
    <dl>
      <dt>Feature version</dt><dd>{item.feature_version}</dd>
      <dt>Instrument / interval</dt><dd>{item.instrument_id} / {item.interval}</dd>
      <dt>Source</dt><dd>{item.source_classification}</dd>
      <dt>First / last timestamp</dt><dd>{new Date(item.first_timestamp).toLocaleString()} / {new Date(item.last_timestamp).toLocaleString()}</dd>
      <dt>Total candles</dt><dd>{item.total_candles}</dd>
      <dt>Usable / warm-up rows</dt><dd>{item.usable_rows} / {item.warmup_rows}</dd>
      <dt>15-minute / 30-minute targets</dt><dd>{item.target_15m_rows} / {item.target_30m_rows}</dd>
      <dt>Null model inputs / invalid</dt><dd>{nullCount} / {availability?.invalid_count ?? 0}</dd>
      <dt>Latest run</dt><dd>{run?.status ?? "unavailable"}</dd>
    </dl>
    {distribution && <div><h3>Experimental target classes</h3>{(["15m", "30m"] as const).map((horizon) => <p key={horizon}>{horizon}: up {distribution.distribution[horizon].up}, down {distribution.distribution[horizon].down}, neutral {distribution.distribution[horizon].neutral}</p>)}</div>}
  </section>;
}
