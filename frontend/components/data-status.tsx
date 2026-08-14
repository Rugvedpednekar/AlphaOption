"use client";

import { useEffect, useState } from "react";
import { fetchIngestionRuns, fetchMarketDataCoverage, type IngestionRun, type MarketDataCoverage } from "@/lib/api";

export function DataStatus() {
  const [coverage, setCoverage] = useState<MarketDataCoverage | null>(null);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  useEffect(() => { const controller = new AbortController(); Promise.all([fetchMarketDataCoverage(controller.signal), fetchIngestionRuns(controller.signal)]).then(([data, result]) => { setCoverage(data); setRuns(result.items); setState("ready"); }).catch(() => setState("error")); return () => controller.abort(); }, []);
  if (state === "loading") return <p role="status">Loading historical coverage…</p>;
  if (state === "error") return <div role="alert">Historical data status is unavailable.</div>;
  if (!coverage || coverage.candle_count === 0) return <section><h2>Data Status</h2><p>No historical candles stored yet.</p></section>;
  return <section>
    {coverage.contains_synthetic_data && <div role="alert" style={{ border: "1px solid var(--amber)", padding: 14, borderRadius: 12, color: "#ffd28b", marginBottom: 18 }}><strong>SYNTHETIC FIXTURE DATA</strong> — not genuine market history and cannot support performance conclusions.</div>}
    <h2>Historical coverage</h2>
    <p>Raw interval gaps count every elapsed interval, including overnight, weekend, and holiday periods; they are not confirmed missing market candles.</p>
    <div style={{ overflowX: "auto" }}><table><thead><tr><th>Instrument role</th><th>Interval</th><th>First candle</th><th>Last candle</th><th>Count</th><th>Raw interval gaps</th></tr></thead><tbody>{coverage.coverage.map((item) => <tr key={`${item.instrument_id}-${item.timeframe}`}><td>{item.instrument_type}{item.is_synthetic ? " (fixture)" : ""}</td><td>{item.timeframe}</td><td>{new Date(item.first_candle).toLocaleString()}</td><td>{new Date(item.last_candle).toLocaleString()}</td><td>{item.candle_count}</td><td>{item.raw_gap_count}</td></tr>)}</tbody></table></div>
    <div style={{ marginTop: 20 }}><h2>Latest ingestion runs</h2>{runs.length ? runs.map((run) => <p key={run.id}>{run.provider} / {run.status}: {run.records_inserted} inserted, {run.records_duplicates} duplicates, {run.records_rejected} rejected{run.is_synthetic ? " — fixture" : ""}</p>) : <p>No ingestion runs yet.</p>}</div>
  </section>;
}
