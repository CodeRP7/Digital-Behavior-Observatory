"""Reusable user-journey and funnel analysis for the cleaned analytics export."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EVENTS_PATH = PROCESSED_DIR / "events_processed.csv"
SESSIONS_PATH = PROCESSED_DIR / "session_features.csv"


def extract_event_sequences(events: pd.DataFrame, event_col: str = "event_name") -> pd.DataFrame:
    """Return one row per session with a chronologically ordered event sequence."""
    required = {"session_id", "hit_number", event_col}
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"Events are missing required journey columns: {sorted(missing)}")

    ordered = events.sort_values(["session_id", "hit_number"], kind="stable").copy()
    journeys = (
        ordered.groupby("session_id", sort=False)[event_col]
        .agg(list)
        .reset_index()
        .rename(columns={event_col: "event_sequence"})
    )
    journeys["journey_length"] = journeys["event_sequence"].map(len)
    journeys["journey_text"] = journeys["event_sequence"].map(" → ".join)
    journeys["sequence_key"] = journeys["event_sequence"].map(tuple)
    return journeys


def identify_first_events(events: pd.DataFrame, event_col: str = "event_name") -> pd.Series:
    """Return the first observed event for each session."""
    ordered = events.sort_values(["session_id", "hit_number"], kind="stable").copy()
    return ordered.groupby("session_id", sort=False)[event_col].first().rename("first_event")


def identify_last_events(events: pd.DataFrame, event_col: str = "event_name") -> pd.Series:
    """Return the final observed event for each session."""
    ordered = events.sort_values(["session_id", "hit_number"], kind="stable").copy()
    return ordered.groupby("session_id", sort=False)[event_col].last().rename("last_event")


def calculate_navigation_depth(events: pd.DataFrame) -> pd.Series:
    """Count page hits within each session as a simple navigation-depth metric."""
    ordered = events.sort_values(["session_id", "hit_number"], kind="stable").copy()
    depth = ordered.groupby("session_id", sort=False)["event_type"].apply(
        lambda values: int((values == "PAGE").sum())
    )
    return depth.rename("navigation_depth")


def calculate_transition_frequencies(
    events: pd.DataFrame, event_col: str = "event_name"
) -> pd.DataFrame:
    """Count consecutive transitions A → B and compute transition probabilities."""
    sequences = extract_event_sequences(events, event_col=event_col)
    transitions = []
    for sequence in sequences["event_sequence"]:
        for previous, current in zip(sequence, sequence[1:]):
            transitions.append({"from_event": previous, "to_event": current})

    if not transitions:
        return pd.DataFrame(columns=["from_event", "to_event", "count", "transition_probability"])

    transition_df = pd.DataFrame(transitions)
    counts = (
        transition_df.groupby(["from_event", "to_event"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    counts["transition_probability"] = counts["count"] / counts["count"].sum()
    counts = counts.sort_values(["count", "from_event", "to_event"], ascending=[False, True, True])
    counts = counts.reset_index(drop=True)
    return counts


def summarize_journey_patterns(
    sessions: pd.DataFrame,
    journeys: pd.DataFrame,
    min_sessions: int = 5,
) -> pd.DataFrame:
    """Summarize the most common full journey patterns with conversion rates."""
    if "session_id" not in journeys.columns or "converted" not in sessions.columns:
        raise ValueError("Both journey and session summary tables are required for journey pattern summaries.")

    pattern_data = journeys[["session_id", "sequence_key", "journey_text", "journey_length"]].merge(
        sessions[["session_id", "converted"]], on="session_id", how="left"
    )
    patterns = (
        pattern_data.groupby("sequence_key", dropna=False)
        .agg(
            sessions=("session_id", "count"),
            conversion_rate=("converted", "mean"),
            journey_text=("journey_text", "first"),
            journey_length=("journey_length", "first"),
        )
        .reset_index()
        .sort_values(["sessions", "conversion_rate"], ascending=[False, False])
        .reset_index(drop=True)
    )
    patterns = patterns[patterns["sessions"] >= min_sessions].copy()
    patterns["journey_pattern"] = patterns["journey_text"]
    return patterns[["journey_pattern", "sessions", "journey_length", "conversion_rate"]]


def build_funnel_summary(events: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    """Define a natural, sequential e-commerce funnel using the actual page and event taxonomy."""
    ordered = events.sort_values(["session_id", "hit_number"], kind="stable").copy()
    all_sessions = pd.Index(sorted(ordered["session_id"].unique()))
    stages = [
        (
            "product_discovery",
            lambda g: (
                g["page_path"].fillna("").str.contains("/google+redesign", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/store.html", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/asearch.html", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/apparel", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/bags", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/drinkware", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/electronics", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/accessories", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/office", case=False, na=False, regex=False)
                | g["page_path"].fillna("").str.contains("/shop+by+brand", case=False, na=False, regex=False)
                | g["event_name"].isin(["Product Click", "Quickview Click"])
            ),
        ),
        (
            "add_to_cart",
            lambda g: g["event_name"].eq("Add to Cart") | g["page_path"].eq("/basket.html"),
        ),
        (
            "checkout",
            lambda g: g["page_path"].isin(
                [
                    "/signin.html",
                    "/myaccount.html?mode=billingaddress",
                    "/myaccount.html?mode=vieworder",
                    "/myaccount.html?mode=vieworderdetail",
                ]
            ),
        ),
        (
            "purchase",
            lambda g: g["page_path"].eq("/ordercompleted.html") | g["transactions"].gt(0),
        ),
    ]

    qualified_by_stage = []
    previous_stage_sessions = all_sessions
    for stage_name, rule in stages:
        passing = []
        for session_id, group in ordered.groupby("session_id", sort=False):
            if session_id not in previous_stage_sessions:
                continue
            first_matching_hit = group.index[rule(group)]
            if not len(first_matching_hit):
                continue
            passing.append(session_id)
        qualified = pd.Index(sorted(passing))
        previous_stage_sessions = qualified
        qualified_by_stage.append(
            {
                "stage": stage_name,
                "qualified_sessions": qualified,
                "stage_count": len(qualified),
            }
        )

    funnel_rows = []
    prior_count = len(all_sessions)
    for stage in qualified_by_stage:
        stage_count = stage["stage_count"]
        funnel_rows.append(
            {
                "stage": stage["stage"],
                "stage_count": stage_count,
                "stage_conversion": (stage_count / prior_count) if prior_count else 0.0,
                "cumulative_conversion": (stage_count / len(all_sessions)) if len(all_sessions) else 0.0,
                "drop_off_count": prior_count - stage_count if prior_count else 0,
                "drop_off_percent": ((prior_count - stage_count) / prior_count) if prior_count else 0.0,
            }
        )
        prior_count = stage_count

    funnel_df = pd.DataFrame(funnel_rows)
    funnel_df = funnel_df[
        ["stage", "stage_count", "stage_conversion", "cumulative_conversion", "drop_off_count", "drop_off_percent"]
    ]
    funnel_df["stage_conversion"] = funnel_df["stage_conversion"].map(lambda x: round(float(x), 4))
    funnel_df["cumulative_conversion"] = funnel_df["cumulative_conversion"].map(lambda x: round(float(x), 4))
    funnel_df["drop_off_percent"] = funnel_df["drop_off_percent"].map(lambda x: round(float(x), 4))
    return funnel_df


def build_session_journey_summary(events: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    """Create a session-level journey table with key behavioral summary fields."""
    ordered = events.sort_values(["session_id", "hit_number"], kind="stable").copy()
    journeys = extract_event_sequences(ordered)
    first_event = identify_first_events(ordered)
    last_event = identify_last_events(ordered)
    navigation_depth = calculate_navigation_depth(ordered)

    journey_summary = journeys.merge(
        sessions[["session_id", "user_id", "session_start", "session_end", "event_count", "converted", "transaction_count", "entry_page", "exit_page"]],
        on="session_id",
        how="left",
    )
    journey_summary = journey_summary.merge(first_event.rename("first_event"), on="session_id", how="left")
    journey_summary = journey_summary.merge(last_event.rename("last_event"), on="session_id", how="left")
    journey_summary = journey_summary.merge(navigation_depth.rename("navigation_depth"), on="session_id", how="left")
    journey_summary["unique_events"] = journey_summary["event_sequence"].map(lambda values: len(set(values)))
    journey_summary["user_id"] = journey_summary["user_id"].astype("string")
    journey_summary = journey_summary.sort_values("session_id", kind="stable").reset_index(drop=True)
    return journey_summary


def main() -> None:
    if not EVENTS_PATH.exists() or not SESSIONS_PATH.exists():
        raise FileNotFoundError("Processed event/session tables are missing. Run `python -m src.preprocessing` first.")

    events = pd.read_csv(
        EVENTS_PATH,
        dtype={"user_id": "string", "source_session_id": "string", "session_id": "string"},
        parse_dates=["event_timestamp", "session_start_timestamp"],
    )
    sessions = pd.read_csv(
        SESSIONS_PATH,
        dtype={"user_id": "string", "session_id": "string"},
        parse_dates=["session_start", "session_end"],
    )

    journeys = build_session_journey_summary(events, sessions)
    transitions = calculate_transition_frequencies(events)
    patterns = summarize_journey_patterns(sessions, journeys, min_sessions=5)
    funnel = build_funnel_summary(events, sessions)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    journeys.to_csv(PROCESSED_DIR / "session_journeys.csv", index=False)
    transitions.to_csv(PROCESSED_DIR / "journey_transitions.csv", index=False)
    patterns.to_csv(PROCESSED_DIR / "journey_patterns.csv", index=False)
    funnel.to_csv(PROCESSED_DIR / "funnel_summary.csv", index=False)

    print(f"Wrote {len(journeys):,} session journeys to {PROCESSED_DIR / 'session_journeys.csv'}")
    print(f"Wrote {len(transitions):,} transition rows to {PROCESSED_DIR / 'journey_transitions.csv'}")
    print(f"Wrote {len(patterns):,} common journey patterns to {PROCESSED_DIR / 'journey_patterns.csv'}")
    print(f"Wrote {len(funnel):,} funnel rows to {PROCESSED_DIR / 'funnel_summary.csv'}")


if __name__ == "__main__":
    main()
