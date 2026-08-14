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
    vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes("coverage") ? { instruments_stored: 4, candle_count: 4, earliest_candle_timestamp: "2026-08-13T03:45:00Z", latest_candle_timestamp: "2026-08-13T03:45:00Z", contains_synthetic_data: true, scope: "paginated_instruments", gap_method: "raw_interval_slots", coverage: [{ instrument_id: "fixture-id", trading_symbol: "NIFTY TEST", instrument_type: "option", timeframe: "1m", candle_count: 2, first_candle: "2026-08-13T03:45:00Z", last_candle: "2026-08-13T03:46:00Z", raw_gap_count: 0, gap_method: "raw_interval_slots", is_synthetic: true }] } : url.includes("ingestion-runs") ? { items: [{ id: "run", provider: "fixture", dataset: "history", status: "completed", started_at: "2026-08-13T03:45:00Z", records_received: 2, records_inserted: 2, records_updated: 0, records_duplicates: 0, records_rejected: 0, is_synthetic: true }] } : { service_status: "healthy", application_version: "0.1.0", operating_mode: "paper", live_orders_enabled: false, database: { status: "healthy" }, timestamp_utc: "2026-08-13T00:00:00Z", market_timezone: "Asia/Kolkata" } })));
    render(<Dashboard />); fireEvent.click(screen.getByRole("button", { name: "Data Status" }));
    expect(await screen.findByText("SYNTHETIC FIXTURE DATA")).toBeInTheDocument();
    expect(screen.getByText(/not genuine market history/)).toBeInTheDocument();
    expect(screen.getByText(/2 inserted, 0 duplicates, 0 rejected/)).toBeInTheDocument();
    expect(screen.getByText(/not confirmed missing market candles/)).toBeInTheDocument();
  });
});
