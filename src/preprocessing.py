"""Reproducible cleaning and timestamp engineering for the selected GA export."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "reports" / "day2_data_quality.md"
OPTIONAL_COLUMNS = (
    "page_path",
    "event_category",
    "event_action",
    "event_label",
    "device_type",
    "platform",
    "browser",
    "transactions",
)
IDENTIFIER_COLUMNS = ("user_id", "source_session_id")
NUMERIC_COLUMNS = ("session_start_epoch", "hit_number", "hit_time_ms")
REQUIRED_COLUMNS = {
    *IDENTIFIER_COLUMNS,
    "event_date",
    *NUMERIC_COLUMNS,
    "event_type",
}


def locate_raw_file(raw_dir: Path = RAW_DIR) -> Path:
    """Require one unambiguous CSV export in data/raw."""
    files = sorted(
        path for path in raw_dir.glob("*.csv") if path.is_file() and not path.name.startswith(".")
    )
    if not files:
        raise FileNotFoundError(
            f"No CSV export found in {raw_dir}. Add the selected BigQuery export there."
        )
    if len(files) > 1:
        names = ", ".join(path.name for path in files)
        raise ValueError(
            f"Expected one raw CSV export in {raw_dir}, found {len(files)}: {names}"
        )
    return files[0]


def read_raw_events(path: Path) -> pd.DataFrame:
    """Read identifiers as strings so large numeric IDs retain exact values."""
    return pd.read_csv(
        path,
        dtype={"user_id": "string", "source_session_id": "string"},
        low_memory=False,
    )


def audit_raw_events(raw: pd.DataFrame) -> dict[str, object]:
    """Collect quality indicators without modifying or filtering the raw data."""
    audit: dict[str, object] = {
        "rows": len(raw),
        "columns": len(raw.columns),
        "dtypes": raw.dtypes.astype(str).to_dict(),
        "missing": raw.isna().sum().to_dict(),
        "duplicate_rows": int(raw.duplicated().sum()),
        "cardinality": {
            column: int(raw[column].nunique(dropna=True))
            for column in raw.select_dtypes(include=["object", "string", "category"]).columns
        },
        "missing_columns": sorted(REQUIRED_COLUMNS.difference(raw.columns)),
        "category_counts": {},
    }
    categorical_columns = raw.select_dtypes(
        include=["object", "string", "category"]
    ).columns
    audit["category_counts"] = {
        column: {
            "<missing>" if pd.isna(value) else str(value): int(count)
            for value, count in raw[column].value_counts(dropna=False).head(10).items()
        }
        for column in categorical_columns
        if column not in IDENTIFIER_COLUMNS and raw[column].nunique(dropna=True) <= 20
    }
    if {"source_session_id", "user_id"}.issubset(raw.columns):
        visitor_counts = raw.groupby("source_session_id", dropna=False)["user_id"].nunique()
        audit["source_session_ids_shared_by_users"] = int(visitor_counts.gt(1).sum())
    if {"user_id", "source_session_id"}.issubset(raw.columns):
        session_keys = ["user_id", "source_session_id"]
        grouped = raw.groupby(session_keys, dropna=False, sort=False)
        audit["composite_sessions"] = int(raw[session_keys].drop_duplicates().shape[0])
        audit["session_attribute_conflicts"] = {
            column: int(grouped[column].nunique(dropna=False).gt(1).sum())
            for column in (
                "session_start_epoch",
                "event_date",
                "device_type",
                "platform",
                "browser",
            )
            if column in raw.columns
        }
        audit["duplicate_session_hit_rows"] = (
            int(raw.duplicated(session_keys + ["hit_number"], keep=False).sum())
            if "hit_number" in raw.columns
            else 0
        )
        if {"hit_number", "hit_time_ms"}.issubset(raw.columns):
            ordered = raw.assign(
                _hit_number=pd.to_numeric(raw["hit_number"], errors="coerce"),
                _hit_time_ms=pd.to_numeric(raw["hit_time_ms"], errors="coerce"),
            ).sort_values(session_keys + ["_hit_number"], kind="stable")
            previous = ordered.groupby(session_keys, dropna=False, sort=False)[
                "_hit_time_ms"
            ].shift()
            audit["decreasing_hit_time_rows"] = int(
                ordered["_hit_time_ms"].lt(previous).sum()
            )
            durations = ordered.groupby(session_keys, dropna=False, sort=False)[
                "_hit_time_ms"
            ].agg(["min", "max"])
            audit["session_duration_seconds_quantiles"] = (
                durations["max"].sub(durations["min"]).div(1000).quantile(
                    [0, 0.5, 0.9, 0.95, 0.99, 1]
                ).to_dict()
            )
            audit["session_event_count_quantiles"] = (
                grouped.size().quantile([0, 0.5, 0.9, 0.95, 0.99, 1]).to_dict()
            )
            if "page_path" in raw.columns:
                audit["sessions_with_repeated_page_paths"] = int(
                    grouped["page_path"]
                    .apply(lambda values: values.dropna().duplicated().any())
                    .sum()
                )
            if "session_start_epoch" in raw.columns and "event_date" in raw.columns:
                epoch = pd.to_numeric(raw["session_start_epoch"], errors="coerce")
                offsets = pd.to_numeric(raw["hit_time_ms"], errors="coerce")
                event_dates = pd.to_datetime(
                    epoch, unit="s", utc=True, errors="coerce"
                ) + pd.to_timedelta(offsets, unit="ms", errors="coerce")
                source_dates = pd.to_datetime(
                    raw["event_date"].astype("string"),
                    format="%Y%m%d",
                    errors="coerce",
                )
                audit["source_date_utc_hit_date_mismatches"] = int(
                    event_dates.dt.strftime("%Y%m%d").ne(
                        source_dates.dt.strftime("%Y%m%d")
                    ).sum()
                )
    if "session_start_epoch" in raw.columns:
        epoch = pd.to_numeric(raw["session_start_epoch"], errors="coerce")
        timestamps = pd.to_datetime(epoch, unit="s", utc=True, errors="coerce")
        audit["invalid_session_start_timestamps"] = int(timestamps.isna().sum())
        audit["session_start_utc_range"] = (
            timestamps.min().isoformat() if timestamps.notna().any() else "unavailable",
            timestamps.max().isoformat() if timestamps.notna().any() else "unavailable",
        )
    if "event_date" in raw.columns:
        dates = pd.to_datetime(
            raw["event_date"].astype("string"), format="%Y%m%d", errors="coerce"
        )
        audit["invalid_source_event_dates"] = int(dates.isna().sum())
        audit["source_event_date_range"] = (
            dates.min().date().isoformat() if dates.notna().any() else "unavailable",
            dates.max().date().isoformat() if dates.notna().any() else "unavailable",
        )
    for column in ("hit_number", "hit_time_ms", "transactions"):
        if column in raw.columns:
            values = pd.to_numeric(raw[column], errors="coerce")
            audit[f"{column}_range"] = (
                values.min() if values.notna().any() else "unavailable",
                values.max() if values.notna().any() else "unavailable",
            )
            audit[f"{column}_negative_values"] = int(values.lt(0).sum())
    return audit


def clean_events(raw: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Normalize, validate, and enrich source events while preserving useful fields."""
    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f"Raw export is missing required columns: {sorted(missing)}")

    events = raw.copy()
    for column in OPTIONAL_COLUMNS:
        if column not in events.columns:
            events[column] = pd.NA
    for column in events.select_dtypes(include=["object", "string"]).columns:
        events[column] = events[column].astype("string").str.strip()
        events[column] = events[column].mask(events[column].eq(""), pd.NA)
    events["event_type"] = events["event_type"].str.upper()

    for column in NUMERIC_COLUMNS:
        events[column] = pd.to_numeric(events[column], errors="coerce")
    events["transactions"] = pd.to_numeric(events["transactions"], errors="coerce")
    source_dates = pd.to_datetime(
        events["event_date"].astype("string"), format="%Y%m%d", errors="coerce"
    )
    events["event_date"] = source_dates.dt.strftime("%Y-%m-%d").astype("string")
    events["session_start_timestamp"] = pd.to_datetime(
        events["session_start_epoch"], unit="s", utc=True, errors="coerce"
    )
    events["event_timestamp"] = events["session_start_timestamp"] + pd.to_timedelta(
        events["hit_time_ms"], unit="ms", errors="coerce"
    )

    invalid = (
        events[list(IDENTIFIER_COLUMNS)].isna().any(axis=1)
        | events["event_date"].isna()
        | (
            events["session_start_epoch"].notna()
            & events["session_start_epoch"].mod(1).ne(0)
        )
        | events["session_start_timestamp"].isna()
        | events["event_timestamp"].isna()
        | events["hit_number"].isna()
        | events["hit_number"].le(0)
        | (
            events["hit_number"].notna()
            & events["hit_number"].mod(1).ne(0)
        )
        | events["hit_time_ms"].isna()
        | events["hit_time_ms"].lt(0)
        | (
            events["hit_time_ms"].notna()
            & events["hit_time_ms"].mod(1).ne(0)
        )
        | events["event_type"].isna()
        | events["transactions"].lt(0)
        | (
            events["transactions"].notna()
            & events["transactions"].mod(1).ne(0)
        )
    )
    invalid_records = int(invalid.sum())
    events = events.loc[~invalid].copy()
    events.drop(columns="session_start_epoch", inplace=True)
    duplicates_removed = int(events.duplicated().sum())
    events = events.drop_duplicates().copy()

    events["session_id"] = (
        events["user_id"].astype("string")
        + ":"
        + events["source_session_id"].astype("string")
    )
    events["source_event_date"] = events["event_date"]
    events["event_date"] = events["event_timestamp"].dt.strftime("%Y-%m-%d").astype("string")
    event_day = events["event_timestamp"].dt
    events["hour"] = event_day.hour.astype("int8")
    events["day_of_week"] = event_day.dayofweek.astype("int8")
    events["week"] = event_day.isocalendar().week.astype("int8")
    events["month"] = event_day.month.astype("int8")
    events["is_weekend"] = events["day_of_week"].ge(5)
    events["time_of_day"] = pd.cut(
        events["hour"],
        bins=[-1, 5, 11, 16, 20, 23],
        labels=["night", "morning", "afternoon", "evening", "late night"],
    ).astype("string")
    events["event_name"] = events["event_action"].fillna(events["event_type"])

    for column in ("event_type", "device_type", "platform", "browser", "time_of_day"):
        events[column] = events[column].astype("category")
    events["hit_number"] = pd.to_numeric(
        events["hit_number"].astype("int64"), downcast="integer"
    )
    events["hit_time_ms"] = pd.to_numeric(
        events["hit_time_ms"].astype("int64"), downcast="integer"
    )
    events["transactions"] = events["transactions"].astype("Int64")
    return (
        events.sort_values(["session_id", "hit_number"], kind="stable").reset_index(drop=True),
        invalid_records,
        duplicates_removed,
    )


def write_quality_report(
    source_path: Path,
    report_path: Path,
    raw: pd.DataFrame,
    cleaned: pd.DataFrame,
    sessions: pd.DataFrame,
    audit: dict[str, object],
    invalid_records: int,
    duplicates_removed: int,
) -> None:
    missing = audit["missing"]
    categorical_lines = [
        f"| `{column}` | {count} |"
        for column, count in audit["cardinality"].items()
    ]
    category_examples = [
        f"| `{column}` | `{value}` | {count:,} |"
        for column, values in audit.get("category_counts", {}).items()
        for value, count in values.items()
    ]
    missing_lines = [
        f"| `{column}` | {count:,} |"
        for column, count in missing.items()
    ]
    notes = [
        "- Source session identifiers are not globally unique: "
        f"{audit.get('source_session_ids_shared_by_users', 0):,} values appear under more than one user. "
        "The composite `(user_id, source_session_id)` is used as the session key.",
        "- Duplicate hits, repeated page paths, long sessions, and multiple users sharing a "
        "source session identifier are retained unless a record fails a documented validity check.",
        "- `source_event_date` is preserved because it can differ from the UTC date of a hit. "
        "Derived `event_date` is based on the event timestamp in UTC.",
    ]
    if invalid_records:
        notes.append(f"- {invalid_records:,} rows failed required-field or numeric/timestamp validity checks and were excluded.")
    if duplicates_removed:
        notes.append(f"- {duplicates_removed:,} exact duplicate event rows were removed.")
    attribute_conflicts = audit.get("session_attribute_conflicts", {})
    notes.append(
        "- Composite-session consistency conflicts: "
        + (
            ", ".join(
                f"{column}={count:,}"
                for column, count in attribute_conflicts.items()
            )
            if attribute_conflicts
            else "not measured"
        )
        + "."
    )
    notes.append(
        f"- Duplicate session/hit-number rows: {audit.get('duplicate_session_hit_rows', 0):,}; "
        f"hit-time reversals after hit-number ordering: {audit.get('decreasing_hit_time_rows', 0):,}."
    )
    notes.append(
        f"- Sessions with repeated page paths: {audit.get('sessions_with_repeated_page_paths', 0):,}; "
        f"source-date / UTC hit-date differences: {audit.get('source_date_utc_hit_date_mismatches', 0):,}. "
        "These are described rather than treated as invalid."
    )
    content = f"""# Day 2 data-quality report

## Dataset and coverage

- Raw file: `{source_path.name}`
- Rows before cleaning: {len(raw):,}
- Columns before cleaning: {len(raw.columns):,}
- Rows after cleaning: {len(cleaned):,}
- Users after cleaning: {cleaned['user_id'].nunique():,}
- Sessions after cleaning: {len(sessions):,}
- Source event-date range: {audit.get('source_event_date_range', ('unavailable', 'unavailable'))[0]} to {audit.get('source_event_date_range', ('unavailable', 'unavailable'))[1]}
- Session-start UTC range: {audit.get('session_start_utc_range', ('unavailable', 'unavailable'))[0]} to {audit.get('session_start_utc_range', ('unavailable', 'unavailable'))[1]}
- Exact duplicate rows found before cleaning: {audit['duplicate_rows']:,}

## Input columns and types

| Column | Inferred input type |
|---|---|
"""
    content += "\n".join(
        f"| `{column}` | `{dtype}` |" for column, dtype in audit["dtypes"].items()
    )
    content += """

## Missing values

| Column | Missing rows before cleaning |
|---|---:|
"""
    content += "\n".join(missing_lines)
    content += """

## Categorical cardinality

| Column | Distinct non-null values |
|---|---:|
"""
    content += "\n".join(categorical_lines)
    content += """

## Most frequent categorical values

Top values are shown for low-cardinality categorical inputs (up to 10 values per column). Identifier and high-cardinality free-text columns are excluded from this table.

| Column | Value | Rows |
|---|---|---:|
"""
    content += "\n".join(category_examples)
    content += """

## Data-quality findings and treatment

"""
    content += "\n".join(notes)
    content += f"""
- Invalid timestamps: {audit.get('invalid_session_start_timestamps', 0):,} invalid session-start values and {audit.get('invalid_source_event_dates', 0):,} invalid source dates.
- Numeric ranges: hit number {audit.get('hit_number_range', ('unavailable', 'unavailable'))[0]}–{audit.get('hit_number_range', ('unavailable', 'unavailable'))[1]}; hit offset {audit.get('hit_time_ms_range', ('unavailable', 'unavailable'))[0]}–{audit.get('hit_time_ms_range', ('unavailable', 'unavailable'))[1]} ms; transactions {audit.get('transactions_range', ('unavailable', 'unavailable'))[0]}–{audit.get('transactions_range', ('unavailable', 'unavailable'))[1]}.
- Negative values before cleaning: hit number {audit.get('hit_number_negative_values', 0):,}; hit offset {audit.get('hit_time_ms_negative_values', 0):,}; transactions {audit.get('transactions_negative_values', 0):,}.
- Session event-count quantiles (min, median, p90, p95, p99, max): {audit.get('session_event_count_quantiles', {})}.
- Session duration-second quantiles (min, median, p90, p95, p99, max): {audit.get('session_duration_seconds_quantiles', {})}.
- Cleaned event timestamps parsed successfully: {cleaned['event_timestamp'].notna().sum():,}/{len(cleaned):,}.
- Non-negative session durations: {int(sessions['session_duration_seconds'].ge(0).sum()):,}/{len(sessions):,}.
- Session device/browser/platform consistency is validated by construction from source-session groups; conflicting attribute values are not silently reconciled.
- Missing event category/action/label and transaction values are preserved at event level. Event metadata is absent on page hits by design; a positive session transaction count is the observed conversion signal.

No observation was removed solely because it was unusually long, had repeated pages/actions, or had a high hit count.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")


def run_pipeline() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Run raw-data audit, cleaning, timestamp engineering, and sessionization."""
    raw_path = locate_raw_file()
    raw = read_raw_events(raw_path)
    audit = audit_raw_events(raw)
    events, invalid_records, duplicates_removed = clean_events(raw)

    from src.session_builder import build_session_features

    sessions = build_session_features(events)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    events.to_csv(PROCESSED_DIR / "events_processed.csv", index=False)
    sessions.to_csv(PROCESSED_DIR / "session_features.csv", index=False)
    write_quality_report(
        raw_path,
        REPORT_PATH,
        raw,
        events,
        sessions,
        audit,
        invalid_records,
        duplicates_removed,
    )
    print(
        f"Processed {len(raw):,} raw rows into {len(events):,} events "
        f"and {len(sessions):,} sessions."
    )
    print(f"Quality report: {REPORT_PATH}")
    return events, sessions, audit


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
