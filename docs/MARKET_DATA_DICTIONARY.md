# Market Data Dictionary

All canonical timestamps are timezone-aware and stored in UTC. Exchange-session interpretation uses `Asia/Kolkata`. Prices use decimal units of the quoted instrument; strikes use index points; volume/open interest use whole contracts or provider-reported units. Providers remain responsible for documenting any different native unit before normalization.

## `instruments`

| Field | Type | Nullable | Meaning and rule |
| --- | --- | --- | --- |
| `id` | UUID | No | Internal provider-independent identifier; primary key. |
| `provider` | varchar(40) | No | Lowercase source-provider key, for example `fixture`. |
| `exchange` | varchar(20) | No | Exchange/segment key. |
| `token` | varchar(100) | No | Provider instrument identifier. Unique with provider and exchange. |
| `trading_symbol` | varchar(160) | No | Provider trading symbol. |
| `underlying_symbol` | varchar(80) | No | Canonical underlying, `NIFTY` in the fixture. |
| `instrument_type` | varchar(20) | No | `spot`, `future`, or `option`. |
| `expiry` | date | Yes | Required for futures/options; absent for spot. |
| `strike` | numeric(18,4) | Yes | Required for options; absent otherwise. |
| `option_type` | varchar(4) | Yes | `CE` or `PE` for options; absent otherwise. |
| `lot_size` | integer | No | Positive exchange-valid lot size. |
| `tick_size` | numeric(12,6) | No | Positive minimum price increment. |
| `active` | boolean | No | Whether metadata currently marks the instrument active. |
| `is_synthetic` | boolean | No | True only for generated fixture/test records. |
| `created_at` | timestamptz | No | UTC database creation timestamp. |
| `updated_at` | timestamptz | No | UTC last metadata update timestamp. |

Constraints enforce valid type/option combinations, positive lot/tick values, nonnegative strikes, and unique `(provider, exchange, token)`.

## `market_candles`

| Field | Type | Nullable | Meaning and rule |
| --- | --- | --- | --- |
| `id` | UUID | No | Primary key. |
| `instrument_id` | UUID FK | No | References `instruments.id`; cascade delete. |
| `timeframe` | varchar(10) | No | Canonical bounded value: `1m`, `5m`, `15m`, `30m`, `1h`, or `1d`. |
| `candle_timestamp` | timestamptz | No | UTC candle start timestamp. |
| `open/high/low/close` | numeric(20,6) | No | Nonnegative prices; high is at least open/close/low and low at most open/close/high. |
| `volume` | bigint | No | Nonnegative provider-reported volume. |
| `open_interest` | bigint | Yes | Nonnegative when supplied; null means unavailable, not zero. |
| `source` | varchar(60) | No | Dataset/source key such as `synthetic_fixture`. |
| `is_synthetic` | boolean | No | True for fixture/test data. |
| `ingested_at` | timestamptz | No | UTC persistence timestamp. |

Unique `(instrument_id, timeframe, candle_timestamp, source)` prevents duplicate canonical observations. Identical repeats are no-ops; conflicting repeats are rejected and audited rather than silently overwritten.

## `ingestion_runs`

| Field | Type | Nullable | Meaning and rule |
| --- | --- | --- | --- |
| `id` | UUID | No | Primary key. |
| `provider` | varchar(40) | No | Provider key. |
| `dataset` | varchar(100) | No | Non-sensitive dataset label. |
| `status` | varchar(20) | No | `running`, `completed`, `completed_with_rejections`, or `failed`. |
| `started_at` | timestamptz | No | UTC start time. |
| `completed_at` | timestamptz | Yes | UTC completion time; null only while running. |
| `records_received` | integer | No | Total instrument and candle records received. |
| `records_inserted` | integer | No | New rows inserted. |
| `records_updated` | integer | No | Instrument metadata rows changed. Candles are immutable. |
| `records_rejected` | integer | No | Validation or conflict rejections. |
| `error_summary` | text | Yes | Redacted bounded summary; never credentials, tokens, environment dumps, or raw auth errors. |
| `is_synthetic` | boolean | No | True when the run contains synthetic fixture data. |

All counters are nonnegative. Application logic sets completion timestamps and terminal status together.
