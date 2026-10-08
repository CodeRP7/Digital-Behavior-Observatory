"""Build session-level behavioral features from cleaned Google Analytics events."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EVENTS_PATH = PROCESSED_DIR / "events_processed.csv"
SESSIONS_PATH = PROCESSED_DIR / "session_features.csv"


def build_session_features(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate cleaned events using the source user and visit identifiers."""
    required = {
        "session_id",
        "user_id",
        "source_session_id",
        "event_timestamp",
        "event_name",
        "event_type",
        "page_path",
        "event_action",
        "hit_number",
        "transactions",
    }
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"Cleaned events are missing required columns: {sorted(missing)}")
    if events["session_id"].isna().any():
        raise ValueError("Cleaned events contain missing session IDs.")

    ordered = events.sort_values(["session_id", "hit_number"], kind="stable")
    duplicate_hits = ordered.duplicated(["session_id", "hit_number"], keep=False)
    if duplicate_hits.any():
        raise ValueError(
            f"Found {int(duplicate_hits.sum()):,} events with duplicate session/hit numbers."
        )
    previous_timestamp = ordered.groupby("session_id", sort=False, observed=True)[
        "event_timestamp"
    ].shift()
    if ordered["event_timestamp"].lt(previous_timestamp).any():
        raise ValueError("Event timestamps decrease within a session's hit-number order.")

    consistency_columns = (
        "user_id",
        "source_session_id",
        "session_start_timestamp",
        "source_event_date",
        "device_type",
        "platform",
        "browser",
    )
    for column in consistency_columns:
        if column in ordered.columns:
            conflicts = (
                ordered.groupby("session_id", sort=False, observed=True)[column]
                .nunique(dropna=False)
                .gt(1)
            )
            if conflicts.any():
                raise ValueError(
                    f"Found {int(conflicts.sum()):,} sessions with conflicting {column} values."
                )

    grouped = ordered.groupby("session_id", sort=False, observed=True)
    sessions = grouped.agg(
        user_id=("user_id", "first"),
        source_session_id=("source_session_id", "first"),
        session_start=("event_timestamp", "min"),
        session_end=("event_timestamp", "max"),
        event_count=("event_timestamp", "size"),
        unique_event_count=("event_name", "nunique"),
        unique_page_count=("page_path", "nunique"),
        unique_action_count=("event_action", "nunique"),
        navigation_depth=("event_type", lambda values: values.eq("PAGE").sum()),
        repeated_action_count=(
            "event_action",
            lambda values: int(values.notna().sum() - values.dropna().nunique()),
        ),
        first_event=("event_name", "first"),
        last_event=("event_name", "last"),
        device_type=("device_type", "first"),
        platform=("platform", "first"),
        browser=("browser", "first"),
        transaction_count=("transactions", "max"),
    )
    page_events = ordered.loc[ordered["page_path"].notna()]
    page_grouped = page_events.groupby("session_id", sort=False, observed=True)["page_path"]
    entry_exit = pd.DataFrame(
        {
            "entry_page": page_grouped.first(),
            "exit_page": page_grouped.last(),
        }
    )
    sessions = sessions.join(entry_exit)
    sessions["transaction_count"] = sessions["transaction_count"].fillna(0).astype("int64")
    sessions["converted"] = sessions["transaction_count"].gt(0)
    sessions["session_duration_seconds"] = (
        sessions["session_end"] - sessions["session_start"]
    ).dt.total_seconds()
    positive_duration = sessions["session_duration_seconds"].gt(0)
    sessions["events_per_minute"] = pd.NA
    sessions.loc[positive_duration, "events_per_minute"] = (
        sessions.loc[positive_duration, "event_count"]
        / (sessions.loc[positive_duration, "session_duration_seconds"] / 60)
    )
    sessions["events_per_minute"] = pd.to_numeric(
        sessions["events_per_minute"], errors="coerce"
    )
    sessions["session_date"] = sessions["session_start"].dt.strftime("%Y-%m-%d")
    sessions["hour"] = sessions["session_start"].dt.hour.astype("int8")
    sessions["day_of_week"] = sessions["session_start"].dt.dayofweek.astype("int8")
    sessions["week"] = sessions["session_start"].dt.isocalendar().week.astype("int8")
    sessions["month"] = sessions["session_start"].dt.month.astype("int8")
    sessions["is_weekend"] = sessions["day_of_week"].ge(5)
    sessions["time_of_day"] = pd.cut(
        sessions["hour"],
        bins=[-1, 5, 11, 16, 20, 23],
        labels=["night", "morning", "afternoon", "evening", "late night"],
    ).astype("string")
    sessions.index.name = "session_id"
    return sessions.reset_index()


def main() -> None:
    if not EVENTS_PATH.exists():
        raise FileNotFoundError(
            f"Processed events not found at {EVENTS_PATH}. "
            "Run `python -m src.preprocessing` first."
        )
    events = pd.read_csv(
        EVENTS_PATH,
        dtype={"user_id": "string", "source_session_id": "string", "session_id": "string"},
        parse_dates=["event_timestamp"],
    )
    sessions = build_session_features(events)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sessions.to_csv(SESSIONS_PATH, index=False)
    print(f"Wrote {len(sessions):,} sessions to {SESSIONS_PATH}")


if __name__ == "__main__":
    main()
