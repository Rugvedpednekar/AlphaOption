export type ServiceState = "healthy" | "degraded";
export type DatabaseState = "healthy" | "unhealthy";

export interface SystemStatus {
  service_status: ServiceState;
  application_version: string;
  operating_mode: "backtest" | "replay" | "paper";
  live_orders_enabled: false;
  database: { status: DatabaseState };
  timestamp_utc: string;
  market_timezone: "Asia/Kolkata";
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
  const response = await fetch(`${API_URL}/api/system/status`, {
    signal,
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Backend returned ${response.status}`);
  return (await response.json()) as SystemStatus;
}
