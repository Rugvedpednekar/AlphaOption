"use client";

import { Activity, CircleOff, Database, IndianRupee, LayoutDashboard, Settings, ShieldCheck, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/empty-state";
import { StatusCard } from "@/components/status-card";
import { fetchSystemStatus, type SystemStatus } from "@/lib/api";
import { DataStatus } from "@/components/data-status";
import { FeatureStatus } from "@/components/feature-status";

const navigation = ["Overview", "Data Status", "Feature Status", "Backtests", "Market Replay", "Paper Trading", "Trades", "System Health", "Settings"] as const;
type Page = (typeof navigation)[number];

export function Dashboard() {
  const [page, setPage] = useState<Page>("Overview");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchSystemStatus(controller.signal).then((data) => { setStatus(data); setError(false); }).catch(() => setError(true)).finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const apiValue = loading ? "Checking…" : error ? "Unavailable" : status?.service_status === "healthy" ? "Healthy" : "Degraded";
  const dbValue = loading ? "Checking…" : error ? "Unknown" : status?.database.status === "healthy" ? "Healthy" : "Unhealthy";
  const healthPage = page === "System Health";

  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "250px minmax(0, 1fr)" }}>
      <aside style={{ borderRight: "1px solid var(--line)", padding: "28px 18px", background: "rgba(3,12,10,.68)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "0 10px 30px" }}><div style={{ width: 38, height: 38, borderRadius: 12, background: "var(--mint)", color: "#062019", display: "grid", placeItems: "center", fontWeight: 900 }}>A</div><div><strong>AlphaOption</strong><small style={{ display: "block", color: "var(--muted)" }}>Research console</small></div></div>
        <nav aria-label="Primary navigation">{navigation.map((item) => <button key={item} onClick={() => setPage(item)} aria-current={page === item ? "page" : undefined} style={{ width: "100%", border: 0, cursor: "pointer", textAlign: "left", color: page === item ? "var(--mint)" : "#b7c8c2", background: page === item ? "rgba(73,224,172,.1)" : "transparent", borderRadius: 12, padding: "12px 14px", marginBottom: 5 }}>{item}</button>)}</nav>
        <div style={{ marginTop: 32, padding: 14, border: "1px solid rgba(73,224,172,.2)", borderRadius: 14, color: "var(--muted)", fontSize: 12 }}><ShieldCheck size={18} color="var(--mint)" /><p style={{ marginBottom: 0 }}>Safety gate active<br />No order routes exist.</p></div>
      </aside>
      <main style={{ padding: "28px clamp(22px,4vw,64px) 60px", overflow: "hidden" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, marginBottom: 24 }}><div><p style={{ color: "var(--mint)", margin: 0, fontSize: 12, letterSpacing: ".18em", textTransform: "uppercase" }}>Local research environment</p><h1 style={{ fontSize: 34, margin: "6px 0" }}>{page}</h1></div><span style={{ padding: "9px 13px", borderRadius: 999, border: "1px solid var(--line)", color: "var(--muted)", fontSize: 13 }}>Asia/Kolkata</span></header>
        <div role="status" style={{ background: "linear-gradient(90deg, rgba(240,184,91,.18), rgba(240,184,91,.06))", border: "1px solid rgba(240,184,91,.44)", color: "#ffd28b", borderRadius: 14, padding: "14px 18px", fontWeight: 800, letterSpacing: ".06em", marginBottom: 28 }}>PAPER TRADING — NO REAL ORDERS</div>
        {page === "Data Status" ? <DataStatus /> : page === "Feature Status" ? <FeatureStatus /> : (page === "Overview" || healthPage) ? <>
          {error && <div role="alert" style={{ color: "#ffd0d0", background: "rgba(255,123,123,.1)", border: "1px solid rgba(255,123,123,.3)", padding: 14, borderRadius: 12, marginBottom: 18 }}>Backend unavailable. The dashboard remains read-only; no trading action is possible.</div>}
          {!error && status?.database.status === "unhealthy" && <div role="alert" style={{ color: "#ffd28b", background: "rgba(240,184,91,.1)", border: "1px solid rgba(240,184,91,.3)", padding: 14, borderRadius: 12, marginBottom: 18 }}>PostgreSQL is unhealthy. Backend status is degraded.</div>}
          <section aria-label="System status" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 16 }}>
            <StatusCard label="Operating mode" value={status?.operating_mode.toUpperCase() ?? (loading ? "Checking…" : "PAPER")} detail="Immutable for each job" tone="good" icon={<LayoutDashboard size={20} />} />
            <StatusCard label="Backend API" value={apiValue} detail={status ? `Version ${status.application_version}` : "FastAPI on port 8000"} tone={error ? "bad" : status?.service_status === "degraded" ? "warning" : loading ? "neutral" : "good"} icon={<Activity size={20} />} />
            <StatusCard label="PostgreSQL" value={dbValue} detail="Local container database" tone={status?.database.status === "unhealthy" ? "bad" : error || loading ? "neutral" : "good"} icon={<Database size={20} />} />
            <StatusCard label="Live orders" value="Disabled" detail="No live endpoints or adapters" tone="good" icon={<CircleOff size={20} />} />
            <StatusCard label="Market data" value="Historical foundation" detail="Genuine and fixture coverage distinguished" icon={<WifiOff size={20} />} />
            <StatusCard label="Active strategy" value="None" detail="Strategies are out of scope" icon={<Settings size={20} />} />
            <StatusCard label="Virtual capital" value="₹20,000" detail="Initial simulation assumption" tone="warning" icon={<IndianRupee size={20} />} />
            <StatusCard label="Open positions" value="None" detail="No broker implementation" tone="good" icon={<ShieldCheck size={20} />} />
          </section>
          <section style={{ marginTop: 24, padding: 22, background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 18 }}><h2 style={{ marginTop: 0, fontSize: 17 }}>Environment note</h2><p style={{ color: "var(--muted)", lineHeight: 1.7, marginBottom: 0 }}>Historical coverage includes one bounded genuine spot-index sample plus clearly labeled fixtures. Strategies, models, backtests, brokers, trades, positions, and performance metrics remain intentionally absent.</p></section>
        </> : <EmptyState title={page} />}
      </main>
    </div>
  );
}
