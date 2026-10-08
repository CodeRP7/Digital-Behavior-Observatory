# Day 2 data-quality report

## Dataset and coverage

- Raw file: `job_6F2X3D4I4WYOCbuT4Xk6DlfekLPe.csv`
- Rows before cleaning: 13,233
- Columns before cleaning: 15
- Rows after cleaning: 13,233
- Users after cleaning: 2,293
- Sessions after cleaning: 2,556
- Source event-date range: 2017-08-01 to 2017-08-01
- Session-start UTC range: 2017-08-01T07:00:40+00:00 to 2017-08-02T06:59:53+00:00
- Exact duplicate rows found before cleaning: 0

## Input columns and types

| Column | Inferred input type |
|---|---|
| `user_id` | `string` |
| `source_session_id` | `string` |
| `event_date` | `int64` |
| `session_start_epoch` | `int64` |
| `hit_number` | `int64` |
| `event_type` | `object` |
| `page_path` | `object` |
| `event_category` | `object` |
| `event_action` | `object` |
| `event_label` | `object` |
| `hit_time_ms` | `int64` |
| `device_type` | `object` |
| `platform` | `object` |
| `browser` | `object` |
| `transactions` | `float64` |

## Missing values

| Column | Missing rows before cleaning |
|---|---:|
| `user_id` | 0 |
| `source_session_id` | 0 |
| `event_date` | 0 |
| `session_start_epoch` | 0 |
| `hit_number` | 0 |
| `event_type` | 0 |
| `page_path` | 0 |
| `event_category` | 10,968 |
| `event_action` | 10,968 |
| `event_label` | 11,950 |
| `hit_time_ms` | 0 |
| `device_type` | 0 |
| `platform` | 0 |
| `browser` | 0 |
| `transactions` | 11,511 |

## Categorical cardinality

| Column | Distinct non-null values |
|---|---:|
| `user_id` | 2293 |
| `source_session_id` | 2509 |
| `event_type` | 2 |
| `page_path` | 314 |
| `event_category` | 2 |
| `event_action` | 6 |
| `event_label` | 175 |
| `device_type` | 3 |
| `platform` | 9 |
| `browser` | 15 |

## Most frequent categorical values

Top values are shown for low-cardinality categorical inputs (up to 10 values per column). Identifier and high-cardinality free-text columns are excluded from this table.

| Column | Value | Rows |
|---|---|---:|
| `event_type` | `PAGE` | 10,939 |
| `event_type` | `EVENT` | 2,294 |
| `event_category` | `<missing>` | 10,968 |
| `event_category` | `Enhanced Ecommerce` | 2,247 |
| `event_category` | `Contact Us` | 18 |
| `event_action` | `<missing>` | 10,968 |
| `event_action` | `Quickview Click` | 1,265 |
| `event_action` | `Add to Cart` | 494 |
| `event_action` | `Product Click` | 411 |
| `event_action` | `Remove from Cart` | 75 |
| `event_action` | `Onsite Click` | 18 |
| `event_action` | `Promotion Click` | 2 |
| `device_type` | `desktop` | 10,206 |
| `device_type` | `mobile` | 2,716 |
| `device_type` | `tablet` | 311 |
| `platform` | `Macintosh` | 5,014 |
| `platform` | `Windows` | 3,307 |
| `platform` | `Android` | 1,826 |
| `platform` | `iOS` | 1,164 |
| `platform` | `Linux` | 975 |
| `platform` | `Chrome OS` | 914 |
| `platform` | `(not set)` | 23 |
| `platform` | `Windows Phone` | 6 |
| `platform` | `Samsung` | 4 |
| `browser` | `Chrome` | 10,896 |
| `browser` | `Safari` | 1,260 |
| `browser` | `Firefox` | 390 |
| `browser` | `Android Webview` | 363 |
| `browser` | `Internet Explorer` | 107 |
| `browser` | `Edge` | 63 |
| `browser` | `Opera` | 55 |
| `browser` | `Safari (in-app)` | 33 |
| `browser` | `Opera Mini` | 29 |
| `browser` | `UC Browser` | 22 |

## Data-quality findings and treatment

- Source session identifiers are not globally unique: 47 values appear under more than one user. The composite `(user_id, source_session_id)` is used as the session key.
- Duplicate hits, repeated page paths, long sessions, and multiple users sharing a source session identifier are retained unless a record fails a documented validity check.
- `source_event_date` is preserved because it can differ from the UTC date of a hit. Derived `event_date` is based on the event timestamp in UTC.
- Composite-session consistency conflicts: session_start_epoch=0, event_date=0, device_type=0, platform=0, browser=0.
- Duplicate session/hit-number rows: 0; hit-time reversals after hit-number ordering: 0.
- Sessions with repeated page paths: 974; source-date / UTC hit-date differences: 3,356. These are described rather than treated as invalid.
- Invalid timestamps: 0 invalid session-start values and 0 invalid source dates.
- Numeric ranges: hit number 1–302; hit offset 0–5454983 ms; transactions 1.0–2.0.
- Negative values before cleaning: hit number 0; hit offset 0; transactions 0.
- Session event-count quantiles (min, median, p90, p95, p99, max): {0.0: 1.0, 0.5: 2.0, 0.9: 13.0, 0.95: 21.0, 0.99: 47.44999999999982, 1.0: 302.0}.
- Session duration-second quantiles (min, median, p90, p95, p99, max): {0.0: 0.0, 0.5: 4.882, 0.9: 484.2755, 0.95: 913.311, 0.99: 2271.581049999981, 1.0: 5454.983}.
- Cleaned event timestamps parsed successfully: 13,233/13,233.
- Non-negative session durations: 2,556/2,556.
- Session device/browser/platform consistency is validated by construction from source-session groups; conflicting attribute values are not silently reconciled.
- Missing event category/action/label and transaction values are preserved at event level. Event metadata is absent on page hits by design; a positive session transaction count is the observed conversion signal.

No observation was removed solely because it was unusually long, had repeated pages/actions, or had a high hit count.
