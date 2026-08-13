"use client";

import { useEffect, useState } from "react";
import { fetchIngestionRuns, fetchMarketDataCoverage, type IngestionRun, type MarketDataCoverage } from "@/lib/api";
import { StatusCard } from "@/components/status-card";

export function DataStatus() {
  const [coverage, setCoverage] = useState<MarketDataCoverage | null>(null);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  useEffect(() => { const controller = new AbortController(); Promise.all([fetchMarketDataCoverage(controller.signal), fetchIngestionRuns(controller.signal)]).then(([data, result]) => { setCoverage(data); setRuns(result.items); setState("ready"); }).catch(() => setState("error")); return () => controller.abort(); }, []);
  if (state === "loading") return <p role="status">Loading market-data coverage…</p>;
  if (state === "error") return <div role="alert">Market-data status is unavailable.</div>;
  if (!coverage || coverage.candle_count === 0) return <section><h2>Data Status</h2><p>No market data stored yet.</p></section>;
  return <section>
    {coverage.contains_synthetic_data && <div role="alert" style={{ border: "1px solid var(--amber)", padding: 14, borderRadius: 12, color: "#ffd28b", marginBottom: 18 }}><strong>SYNTHETIC TEST DATA</strong> — not genuine market history and not trading performance.</div>}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 16 }}>
      <StatusCard label="Instruments stored" value={String(coverage.instruments_stored)} />
      <StatusCard label="Candles stored" value={String(coverage.candle_count)} />
      <StatusCard label="Earliest candle" value={coverage.earliest_candle_timestamp ? new Date(coverage.earliest_candle_timestamp).toLocaleString() : "None"} />
      <StatusCard label="Latest candle" value={coverage.latest_candle_timestamp ? new Date(coverage.latest_candle_timestamp).toLocaleString() : "None"} />
    </div>
    <div style={{ marginTop: 20, background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 16, padding: 18 }}><h2>Coverage</h2>{coverage.coverage.map((item) => <p key={`${item.instrument_type}-${item.timeframe}`}>{item.instrument_type} · {item.timeframe}: {item.candle_count} candles</p>)}</div>
    <div style={{ marginTop: 20, background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 16, padding: 18 }}><h2>Recent ingestion runs</h2>{runs.length ? runs.map((run) => <p key={run.id}>{run.provider} / {run.dataset}: {run.status} ({run.records_inserted} inserted){run.is_synthetic ? " — synthetic" : ""}</p>) : <p>No ingestion runs yet.</p>}</div>
  </section>;
}
