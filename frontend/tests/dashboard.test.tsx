import { render, screen } from "@testing-library/react";
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
