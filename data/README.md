# Data dictionary and reproducibility

## Selected dataset and raw input

The selected source is the public Google Analytics Universal Analytics sample dataset in BigQuery:

- Project: `bigquery-public-data`
- Dataset: `google_analytics_sample`
- Table used for this export: `ga_sessions_20170801`
- Coverage: sessions with source date `2017-08-01`
- Local export filename observed for this run: `job_6F2X3D4I4WYOCbuT4Xk6DlfekLPe.csv`

This is the older Universal Analytics session schema, not the GA4 `events_*` schema. The public source has obfuscated fields and is intended for learning and analysis. BigQuery access and export steps are described in [Google's sample dataset documentation](https://support.google.com/analytics/answer/7586738?hl=en).

The raw CSV belongs in `data/raw/`. It is intentionally excluded from Git; do not commit it. To reproduce this event export, run the following query in BigQuery and save the results as CSV:

```sql
SELECT
  fullVisitorId AS user_id,
  CAST(visitId AS STRING) AS source_session_id,
  date AS event_date,
  visitStartTime AS session_start_epoch,
  hit.hitNumber AS hit_number,
  hit.type AS event_type,
  hit.page.pagePath AS page_path,
  hit.eventInfo.eventCategory AS event_category,
  hit.eventInfo.eventAction AS event_action,
  hit.eventInfo.eventLabel AS event_label,
  hit.time AS hit_time_ms,
  device.deviceCategory AS device_type,
  device.operatingSystem AS platform,
  device.browser AS browser,
  totals.transactions AS transactions
FROM `bigquery-public-data.google_analytics_sample.ga_sessions_20170801`
CROSS JOIN UNNEST(hits) AS hit
```

## Dataset observed in the local export

The inspected export has 13,233 rows and 15 columns. It contains 2,293 users, 2,509 distinct source session IDs, and 2,556 distinct `(user_id, source_session_id)` pairs. No exact duplicate rows were found. See [the generated quality report](../reports/day2_data_quality.md) for per-column types, missingness, cardinality, timestamp coverage, and validation results.

| Raw column | Meaning |
|---|---|
| `user_id` | Anonymized Google Analytics visitor identifier. Kept as text to avoid numeric precision loss. |
| `source_session_id` | Google Analytics `visitId`; not globally unique across users. |
| `event_date` | Original Google Analytics session date, `YYYYMMDD`. It is retained as `source_event_date` after cleaning. |
| `session_start_epoch` | Session start as Unix seconds; converted to UTC timestamp and not retained as a numeric field in the processed events. |
| `hit_number` | Hit sequence number within the source session. |
| `event_type` | Google Analytics hit type, such as `PAGE` or `EVENT`. |
| `page_path` | Page path when supplied by the hit. |
| `event_category` | Optional event category. Null on page hits in this export. |
| `event_action` | Optional event action. Null on page hits in this export. |
| `event_label` | Optional event label. |
| `hit_time_ms` | Hit offset from the session start in milliseconds. |
| `device_type` | Device category from the source, such as desktop, mobile, or tablet. |
| `platform` | Source operating system. |
| `browser` | Source browser. |
| `transactions` | Nullable session transaction total repeated on each exported hit. |

## Reproducible workflow

From the repository root, run `python -m src.preprocessing`. The pipeline reads the sole CSV in `data/raw/`, audits before filtering, validates required fields, strips surrounding whitespace, uppercases hit types, removes exact duplicate events only, parses timestamps, derives temporal fields, and builds session-level features.

It writes the following artifacts:

- `data/processed/events_processed.csv` — cleaned events with parsed UTC timestamps, source and derived dates, composite session ID, event name, and temporal features (ignored by Git).
- `data/processed/session_features.csv` — one row per composite session with engagement, navigation, temporal, device, and conversion features (ignored by Git).
- `reports/day2_data_quality.md` — input profile, missing-value/cardinality summaries, quality findings, and output validation counts (tracked as a reproducible Day 2 report).

Raw data is read-only in this workflow. The pipeline requires exactly one CSV input to avoid silently choosing among multiple datasets.

## Session definition and cleaning decisions

- The source provides `visitId` and visitor ID. Since 47 source `visitId` values in this export are shared by more than one visitor, the stable session key is the pair `(user_id, source_session_id)`, serialized as `session_id = user_id:source_session_id`. Each pair has consistent start time, date, device, platform, and browser in this export.
- No inactivity re-sessionization is performed: the source already defines the visit/session boundary. Within-session hit order is validated by `hit_number`; long visits and repeated page paths are retained as observed behavior.
- `event_timestamp` is the UTC `session_start_epoch` plus `hit_time_ms`. The raw `event_date` does not always equal the UTC calendar date of a hit, so it is preserved in `source_event_date`; the derived `event_date` is the UTC event date.
- Rows with missing identifiers, invalid source dates/timestamps, absent event type, non-positive or non-integer hit numbers, non-integer session epochs/hit offsets/transaction counts, negative hit offsets, or negative transaction values are invalid. Exact duplicate rows are removed; no unusual records are excluded just for being extreme.
- Missing event category/action/label values are meaningful for non-event hits and remain null. The session conversion indicator is true only when the observed transaction total is positive; a null transaction total is treated as no recorded transaction, not proof of a broader business outcome.
- Time-of-day buckets use UTC hours: night 00–05, morning 06–11, afternoon 12–16, evening 17–20, late night 21–23.

## Processed event columns

The event table retains all 15 source fields except numeric `session_start_epoch`, which becomes `session_start_timestamp`, and adds:

| Derived column | Meaning |
|---|---|
| `session_start_timestamp` | Parsed session-start timestamp in UTC. |
| `event_timestamp` | Session-start timestamp plus hit offset, in UTC. |
| `session_id` | Composite visitor and source visit ID. |
| `source_event_date` | Original source `event_date`, formatted `YYYY-MM-DD`. |
| `event_date` | UTC date derived from `event_timestamp`. |
| `event_name` | `event_action` where present; otherwise `event_type`. |
| `hour` | UTC hour of the hit, 0–23. |
| `day_of_week` | UTC weekday, Monday=0 through Sunday=6. |
| `week` | ISO week number in UTC. |
| `month` | UTC month number. |
| `is_weekend` | Whether the UTC weekday is Saturday or Sunday. |
| `time_of_day` | UTC bucket defined above. |

## Processed session feature columns

| Column | Meaning |
|---|---|
| `session_id`, `user_id`, `source_session_id` | Composite session key and source identifiers. |
| `session_start`, `session_end` | First and last event timestamps in UTC. |
| `session_duration_seconds` | Difference between the last and first event timestamps, in seconds; zero for single-timestamp sessions. |
| `event_count` | Number of exported hits in the session. |
| `unique_event_count` | Distinct event names (`event_action` when present, else hit type). |
| `unique_page_count` | Distinct non-null page paths. |
| `unique_action_count` | Distinct non-null event actions. |
| `navigation_depth` | Count of `PAGE` hits. |
| `repeated_action_count` | Non-null action occurrences beyond the first occurrence of each action. |
| `entry_page`, `exit_page` | First and last non-null page paths in hit order. |
| `first_event`, `last_event` | First and last event names in hit order. |
| `device_type`, `platform`, `browser` | Device context, unchanged from source. |
| `transaction_count`, `converted` | Maximum observed transaction total (null becomes zero) and whether it is positive. |
| `events_per_minute` | Event count divided by session duration in minutes; null for zero-duration sessions. |
| `session_date`, `hour`, `day_of_week`, `week`, `month`, `is_weekend`, `time_of_day` | UTC temporal features derived from session start. |

## Limitations

This is a one-day export, not the complete public sample dataset. Visitor IDs are anonymized, Google Analytics data is obfuscated, and the 43 positive-transaction sessions are only observed conversions in this sample. Session summaries describe completed sessions and should not be used as if they were available before a session ends in a future predictive task. Conversion timing cannot be calculated because transaction timestamps are not included in this export.
