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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
  const response = await fetch(`${API_URL}/api/system/status`, {
    signal,
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Backend returned ${response.status}`);
  return (await response.json()) as SystemStatus;
}

export interface MarketDataCoverage {
  instruments_stored: number;
  candle_count: number;
  earliest_candle_timestamp: string | null;
  latest_candle_timestamp: string | null;
  contains_synthetic_data: boolean;
  scope: "paginated_instruments";
  gap_method: "raw_interval_slots";
  coverage: Array<{ instrument_id: string; instrument_type: string; timeframe: string; candle_count: number; first_candle: string; last_candle: string; raw_gap_count: number; gap_method: "raw_interval_slots"; is_synthetic: boolean }>;
}

export interface IngestionRun {
  id: string; provider: string; dataset: string; status: string; started_at: string;
  records_received: number; records_inserted: number; records_updated: number;
  records_duplicates: number; records_rejected: number; completed_at?: string | null; is_synthetic: boolean;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal, cache: "no-store", headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Backend returned ${response.status}`);
  return (await response.json()) as T;
}

export const fetchMarketDataCoverage = (signal?: AbortSignal) => getJson<MarketDataCoverage>("/api/market-data/coverage", signal);
export const fetchIngestionRuns = (signal?: AbortSignal) => getJson<{ items: IngestionRun[] }>("/api/market-data/ingestion-runs?limit=10", signal);

export interface FeatureCoverageItem {
  instrument_id: string; interval: "5m"; feature_version: string;
  source_classification: "genuine" | "synthetic"; total_candles: number;
  usable_rows: number; warmup_rows: number; first_timestamp: string; last_timestamp: string;
  target_15m_rows: number; target_30m_rows: number;
}
export interface FeatureRun { id: string; status: string; feature_version: string; source_classification: "genuine" | "synthetic"; }
export interface FeatureAvailability { model_input_null_counts: Record<string, number>; target_null_counts: Record<string, number>; invalid_count: number; }
export interface TargetDistribution { distribution: { "15m": { up: number; down: number; neutral: number }; "30m": { up: number; down: number; neutral: number } }; }

export const fetchFeatureCoverage = (signal?: AbortSignal) => getJson<{ items: FeatureCoverageItem[] }>("/api/features/coverage?limit=20", signal);
export const fetchFeatureRuns = (signal?: AbortSignal) => getJson<{ items: FeatureRun[] }>("/api/features/runs?limit=10", signal);
export const fetchFeatureAvailability = (instrumentId: string, version: string, signal?: AbortSignal) => getJson<FeatureAvailability>(`/api/features/availability?instrument_id=${encodeURIComponent(instrumentId)}&feature_version=${encodeURIComponent(version)}`, signal);
export const fetchTargetDistribution = (instrumentId: string, version: string, signal?: AbortSignal) => getJson<TargetDistribution>(`/api/features/target-distribution?instrument_id=${encodeURIComponent(instrumentId)}&feature_version=${encodeURIComponent(version)}`, signal);

export interface BackfillRun {
  id: string; status: string; provider: string; planned_chunks: number;
  successful_chunks: number; empty_chunks: number; skipped_chunks: number; failed_chunks: number;
}
export interface DatasetQuality {
  observed_start: string | null; observed_end: string | null; total_candles: number;
  observed_trading_dates: number; genuine_count: number; synthetic_count: number;
  internal_five_minute_gap_count: number; complete_sessions: number; partial_sessions: number;
  non_regular_sessions: number; ml_readiness: string; regular_session_assumption: string;
  monthly: Array<{ month: string; candles: number; observed_sessions: number; complete_sessions: number; partial_sessions: number }>;
}
export const fetchBackfillRuns = (signal?: AbortSignal) => getJson<{ items: BackfillRun[] }>("/api/market-data/backfill-runs?limit=10", signal);
export const fetchDatasetQuality = (instrumentId: string, signal?: AbortSignal) => getJson<DatasetQuality>(`/api/market-data/dataset-quality?instrument_id=${encodeURIComponent(instrumentId)}&session_limit=1`, signal);
