import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "@/components/dashboard";

afterEach(() => vi.restoreAllMocks());

describe("dashboard safety and health states", () => {
  it("always shows the paper-only safety banner", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<Dashboard />);
    expect(screen.getByText("PAPER TRADING — NO REAL ORDERS")).toBeInTheDocument();
  });

  it("shows healthy API and database state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" }) }));
    render(<Dashboard />);
    expect((await screen.findAllByText("Healthy")).length).toBeGreaterThanOrEqual(2);
  });

  it("shows backend unavailable state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<Dashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  });

  it("shows database unhealthy state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ service_status: "degraded", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "unhealthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" }) }));
    render(<Dashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent("PostgreSQL is unhealthy");
  });
});

describe("Data Status", () => {
  it("shows the historical loading state", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    render(<Dashboard />); fireEvent.click(screen.getByRole("button", { name: "Data Status" }));
    expect(screen.getByText("Loading historical coverage…")).toBeInTheDocument();
  });

  it("shows the historical empty state", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("coverage") ? { instruments_stored: 0, candle_count: 0, earliest_candle_timestamp: null, latest_candle_timestamp: null, contains_synthetic_data: false, coverage: [] } : url.includes("ingestion-runs") ? { items: [] } : { service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" } })));
    render(<Dashboard />); fireEvent.click(screen.getByRole("button", { name: "Data Status" }));
    expect(await screen.findByText("No historical candles stored yet.")).toBeInTheDocument();
  });

  it("shows the historical error state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<Dashboard />); fireEvent.click(screen.getByRole("button", { name: "Data Status" }));
    expect(await screen.findByText("Historical data status is unavailable.")).toBeInTheDocument();
  });

  it("renders coverage with an unmistakable synthetic warning", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("coverage") ? { instruments_stored: 4, candle_count: 4, earliest_candle_timestamp: "2026-08-13T03:45:00Z", latest_candle_timestamp: "2026-08-13T03:45:00Z", contains_synthetic_data: true, scope: "paginated_instruments", gap_method: "raw_interval_slots", coverage: [{ instrument_id: "fixture-id", instrument_type: "option", timeframe: "1m", candle_count: 2, first_candle: "2026-08-13T03:45:00Z", last_candle: "2026-08-13T03:46:00Z", raw_gap_count: 0, gap_method: "raw_interval_slots", is_synthetic: true }] } : url.includes("ingestion-runs") ? { items: [{ id: "run", provider: "fixture", dataset: "history", status: "completed", started_at: "2026-08-13T03:45:00Z", records_received: 2, records_inserted: 2, records_updated: 0, records_duplicates: 0, records_rejected: 0, is_synthetic: true }] } : { service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" } })));
    render(<Dashboard />); fireEvent.click(screen.getByRole("button", { name: "Data Status" }));
    expect(await screen.findByText("SYNTHETIC FIXTURE DATA")).toBeInTheDocument();
    expect(screen.getByText(/not genuine market history/)).toBeInTheDocument();
    expect(screen.getByText(/2 inserted, 0 duplicates, 0 rejected/)).toBeInTheDocument();
    expect(screen.getByText(/not confirmed missing market candles/)).toBeInTheDocument();
  });
});

describe("Feature Status", () => {
  it("shows loading, empty, and error states", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    const loading = render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Feature Status" }));
    expect(screen.getByText("Loading feature status…")).toBeInTheDocument();
    loading.unmount();

    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("/api/features/") ? { items: [] } : { service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" } })));
    const empty = render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Feature Status" }));
    expect(await screen.findByText("No feature rows have been built.")).toBeInTheDocument();
    empty.unmount();

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Feature Status" }));
    expect(await screen.findByText("Feature status is unavailable.")).toBeInTheDocument();
  });

  it("shows leakage safety, aggregates, and synthetic warning", async () => {
    const coverage = { items: [{ instrument_id: "fixture-id", interval: "5m", feature_version: "v1", source_classification: "synthetic", total_candles: 50, usable_rows: 14, warmup_rows: 36, first_timestamp: "2026-08-13T03:45:00Z", last_timestamp: "2026-08-13T07:50:00Z", target_15m_rows: 34, target_30m_rows: 31 }] };
    const run = { items: [{ id: "run", status: "completed", feature_version: "v1", source_classification: "synthetic" }] };
    const availability = { model_input_null_counts: { ema_21: 20 }, target_null_counts: {}, invalid_count: 0 };
    const distribution = { distribution: { "15m": { up: 1, down: 2, neutral: 31 }, "30m": { up: 1, down: 1, neutral: 29 } } };
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("features/coverage") ? coverage : url.includes("features/runs") ? run : url.includes("availability") ? availability : url.includes("target-distribution") ? distribution : { service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" } })));
    render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Feature Status" }));
    expect(await screen.findByText("SYNTHETIC FEATURE DATA")).toBeInTheDocument();
    expect(screen.getByText(/Each model input uses completed candles/)).toBeInTheDocument();
    expect(screen.getByText(/No ML model or backtest exists yet/)).toBeInTheDocument();
    expect(screen.getByText(/up 1, down 2, neutral 31/)).toBeInTheDocument();
  });
});

describe("Dataset Quality", () => {
  it("shows loading, empty, and error states", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    const loading = render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Dataset Quality" }));
    expect(screen.getByText("Loading dataset quality…")).toBeInTheDocument();
    loading.unmount();

    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("coverage") ? { candle_count: 0, coverage: [] } : url.includes("backfill-runs") ? { items: [] } : { service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" } })));
    const empty = render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Dataset Quality" }));
    expect(await screen.findByText("No five-minute dataset is available for assessment.")).toBeInTheDocument();
    empty.unmount();

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Dataset Quality" }));
    expect(await screen.findByText("Dataset quality is unavailable.")).toBeInTheDocument();
  });

  it("shows synthetic-only, monthly, readiness, and safety warnings", async () => {
    const coverage = { candle_count: 75, coverage: [{ instrument_id: "fixture-id", timeframe: "5m" }] };
    const backfills = { items: [{ id: "run", status: "completed", provider: "fixture", planned_chunks: 1, successful_chunks: 1, empty_chunks: 0, skipped_chunks: 0, failed_chunks: 0 }] };
    const quality = { observed_start: "2026-08-13T03:45:00Z", observed_end: "2026-08-13T09:55:00Z", total_candles: 75, observed_trading_dates: 1, genuine_count: 0, synthetic_count: 75, internal_five_minute_gap_count: 0, complete_sessions: 1, partial_sessions: 0, non_regular_sessions: 0, ml_readiness: "insufficient", regular_session_assumption: "Asia/Kolkata regular session; not an official exchange calendar", monthly: [{ month: "2026-08", candles: 75, observed_sessions: 1, complete_sessions: 1, partial_sessions: 0 }] };
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("backfill-runs") ? backfills : url.includes("dataset-quality") ? quality : url.includes("coverage") ? coverage : { service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" } })));
    render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Dataset Quality" }));
    expect(await screen.findByText("SYNTHETIC-ONLY DATASET")).toBeInTheDocument();
    expect(screen.getByText(/2026-08: 75 candles/)).toBeInTheDocument();
    expect(screen.getByText(/does not prove predictability or profitability/)).toBeInTheDocument();
    expect(screen.getByText(/does not establish storage, licensing, or redistribution rights/)).toBeInTheDocument();
  });
});
