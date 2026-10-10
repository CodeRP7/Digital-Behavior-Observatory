"""Behavioral feature engineering and clustering preparation for user segmentation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SESSION_FEATURES_PATH = PROCESSED_DIR / "session_features.csv"
USER_BEHAVIOR_PATH = PROCESSED_DIR / "user_behavior_features.csv"

FEATURE_DOCUMENTATION = {
    "session_count": "Number of sessions attributed to each user; captures repeat usage and engagement frequency.",
    "sessions_per_user": "Alias of session_count for a user-level behavioral frequency measure.",
    "avg_session_duration_seconds": "Average session length in seconds; captures how deeply users spend time in the product.",
    "median_session_duration_seconds": "Median session length; more robust to outliers than the mean.",
    "avg_events_per_session": "Average number of recorded events per session; measures session intensity.",
    "events_per_session": "Alias used in the compact clustering feature set for session intensity.",
    "total_events": "Overall event volume per user; reflects cumulative browsing activity.",
    "active_days": "Number of distinct UTC days a user interacts with the product; captures return behavior.",
    "avg_navigation_depth": "Average page-depth per session; measures browsing breadth within sessions.",
    "avg_unique_event_count": "Average number of distinct event names per session; measures action diversity.",
    "avg_unique_action_count": "Average number of unique action labels per session; captures interaction diversity.",
    "repeated_action_frequency": "Average repeated action count per session; captures repetitive or habitual behavior.",
    "return_frequency": "Sessions divided by active days; indicates how often users return after initial activity.",
}

DEFAULT_FEATURE_COLUMNS = [
    "sessions_per_user",
    "avg_session_duration_seconds",
    "events_per_session",
    "avg_navigation_depth",
    "avg_unique_event_count",
    "return_frequency",
]


def _ensure_required_session_columns(df: pd.DataFrame) -> None:
    required = {
        "user_id",
        "session_id",
        "session_start",
        "session_duration_seconds",
        "event_count",
        "navigation_depth",
        "unique_event_count",
        "unique_action_count",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(
            "Session-level feature table is missing required behavioral columns: "
            + ", ".join(missing)
        )


def _to_numeric_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.astype(float)


def build_behavioral_feature_table(session_features: pd.DataFrame) -> pd.DataFrame:
    """Aggregate session-level behavior into a user-level behavior profile.

    The correct behavioral unit is the user when the dataset contains repeated visits by
    distinct users. This avoids mixing multiple sessions of the same user into a single
    observation and better matches the assignment requirement to discover true audience
    patterns rather than session-only behavior.
    """
    if session_features is None or session_features.empty:
        raise ValueError("Session feature table is empty; cannot build user behavior features.")

    _ensure_required_session_columns(session_features)

    working = session_features.copy()
    working["user_id"] = working["user_id"].astype("string")
    working["session_id"] = working["session_id"].astype("string")
    working["session_start"] = pd.to_datetime(working["session_start"], errors="coerce")
    working["session_duration_seconds"] = _to_numeric_series(working["session_duration_seconds"])
    working["event_count"] = _to_numeric_series(working["event_count"])
    working["navigation_depth"] = _to_numeric_series(working["navigation_depth"])
    working["unique_event_count"] = _to_numeric_series(working["unique_event_count"])
    working["unique_action_count"] = _to_numeric_series(working["unique_action_count"])

    if "session_date" in working.columns:
        working["session_date"] = pd.to_datetime(working["session_date"], errors="coerce")
    if "repeated_action_count" in working.columns:
        working["repeated_action_count"] = _to_numeric_series(working["repeated_action_count"])
    if "converted" in working.columns:
        working["converted"] = working["converted"].astype(bool)

    grouped = working.groupby("user_id", sort=False)
    user_features = grouped.agg(
        session_count=("session_id", "nunique"),
        total_events=("event_count", "sum"),
        avg_session_duration_seconds=("session_duration_seconds", "mean"),
        median_session_duration_seconds=("session_duration_seconds", "median"),
        avg_events_per_session=("event_count", "mean"),
        avg_navigation_depth=("navigation_depth", "mean"),
        avg_unique_event_count=("unique_event_count", "mean"),
        avg_unique_action_count=("unique_action_count", "mean"),
        active_days=("session_start", lambda values: int(values.dropna().dt.date.nunique())),
        first_seen=("session_start", "min"),
        last_seen=("session_start", "max"),
    )

    if "repeated_action_count" in working.columns:
        user_features["repeated_action_frequency"] = (
            grouped["repeated_action_count"].sum() / grouped["session_id"].count()
        )
    else:
        user_features["repeated_action_frequency"] = 0.0

    user_features["events_per_session"] = (
        user_features["total_events"] / user_features["session_count"].replace(0, np.nan)
    )
    user_features["sessions_per_user"] = user_features["session_count"]
    user_features["return_frequency"] = (
        user_features["session_count"] / user_features["active_days"].replace(0, np.nan)
    )

    user_features = user_features.reset_index().rename(columns={"user_id": "user_id"})
    user_features["user_id"] = user_features["user_id"].astype("string")
    user_features["average_session_duration"] = user_features["avg_session_duration_seconds"]
    user_features["average_session_duration_seconds"] = user_features["avg_session_duration_seconds"]
    user_features["average_events_per_session"] = user_features["events_per_session"]
    user_features["average_navigation_depth"] = user_features["avg_navigation_depth"]
    user_features["average_unique_event_count"] = user_features["avg_unique_event_count"]
    user_features["average_unique_action_count"] = user_features["avg_unique_action_count"]
    return user_features


build_feature_table = build_behavioral_feature_table


def select_behavioral_features(
    feature_table: pd.DataFrame,
    feature_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return the compact, interpretable feature set for clustering."""
    if feature_table is None or feature_table.empty:
        raise ValueError("Feature table is empty; cannot select behavioral features.")

    if feature_columns is None:
        feature_columns = DEFAULT_FEATURE_COLUMNS
    selected = list(feature_columns)
    missing = [column for column in selected if column not in feature_table.columns]
    if missing:
        available = list(feature_table.columns)
        raise ValueError(
            "Requested feature columns are not present in the behavior table: "
            + ", ".join(missing)
            + ". Available columns: "
            + ", ".join(available)
        )

    output = feature_table[["user_id", *selected]].copy()
    for column in selected:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    output = output.fillna(0.0)
    return output


select_feature_columns = select_behavioral_features


def prepare_clustering_matrix(
    feature_table: pd.DataFrame,
    feature_columns: Sequence[str] | None = None,
    scale_method: str = "robust",
) -> pd.DataFrame:
    """Prepare the clustering matrix and apply a simple, defensible transformation."""
    selected = select_behavioral_features(feature_table, feature_columns=feature_columns)
    numeric = selected.drop(columns=["user_id"]).copy()

    if numeric.empty:
        raise ValueError("No behavioral features remain after column selection.")

    numeric = numeric.apply(pd.to_numeric, errors="coerce").fillna(0.0)

    if scale_method.lower() == "robust":
        scaler = RobustScaler()
        matrix = scaler.fit_transform(numeric)
    elif scale_method.lower() == "standard":
        scaler = StandardScaler()
        matrix = scaler.fit_transform(numeric)
    elif scale_method.lower() in {"none", "raw"}:
        matrix = numeric.to_numpy(copy=True)
    else:
        raise ValueError(
            "Unknown scale method. Use 'robust', 'standard', or 'none'."
        )

    matrix_df = pd.DataFrame(matrix, index=selected["user_id"], columns=numeric.columns)
    return matrix_df


prepare_clustering_data = prepare_clustering_matrix


def cluster_users(
    feature_table: pd.DataFrame,
    n_clusters: int = 3,
    feature_columns: Sequence[str] | None = None,
    scale_method: str = "robust",
    random_state: int = 42,
    return_model: bool = False,
) -> pd.Series | tuple[pd.Series, KMeans]:
    """Cluster users with K-Means on the compact behavioral feature set."""
    matrix = prepare_clustering_matrix(
        feature_table,
        feature_columns=feature_columns,
        scale_method=scale_method,
    )

    if len(matrix) < 2:
        raise ValueError("At least two users are required to perform clustering.")

    n_clusters = int(min(n_clusters, len(matrix)))
    if n_clusters < 2:
        raise ValueError("n_clusters must be at least 2 for a real clustering comparison.")

    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    labels = model.fit_predict(matrix)
    label_series = pd.Series(labels, index=matrix.index, name="segment_label").astype("int64")
    if return_model:
        return label_series, model
    return label_series


summarize_segments = None


def summarize_user_segments(
    feature_table: pd.DataFrame,
    labels: pd.Series,
    feature_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return cluster-level averages for interpretation and reporting."""
    if labels is None:
        raise ValueError("Labels are required to summarize user segments.")

    merged = feature_table[["user_id", *list(feature_columns or DEFAULT_FEATURE_COLUMNS)]].copy()
    merged["segment_label"] = labels.reindex(merged["user_id"]).to_numpy()
    summary = (
        merged.groupby("segment_label", dropna=False)
        .mean(numeric_only=True)
        .sort_index()
        .reset_index()
    )
    return summary


profile_segments = summarize_user_segments


def main() -> None:
    if not SESSION_FEATURES_PATH.exists():
        raise FileNotFoundError(
            "Session feature table not found. Run `python -m src.preprocessing` and `python -m src.session_builder` first."
        )

    session_features = pd.read_csv(
        SESSION_FEATURES_PATH,
        dtype={"user_id": "string", "session_id": "string"},
    )
    for column in ("session_start", "session_end"):
        if column in session_features.columns:
            session_features[column] = pd.to_datetime(
                session_features[column], format="ISO8601", utc=True, errors="raise"
            )
    user_features = build_behavioral_feature_table(session_features)
    selected = select_behavioral_features(user_features)
    clustering_matrix = prepare_clustering_matrix(selected, scale_method="robust")
    labels = cluster_users(selected, n_clusters=3, scale_method="robust")
    segment_summary = summarize_user_segments(selected, labels)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    user_features.to_csv(USER_BEHAVIOR_PATH, index=False)
    selected.to_csv(PROCESSED_DIR / "user_behavior_cluster_features.csv", index=False)
    clustering_matrix.to_csv(PROCESSED_DIR / "user_behavior_matrix.csv")
    segment_summary.to_csv(PROCESSED_DIR / "user_segment_summary.csv", index=False)

    print(f"Built {len(user_features):,} user behavior rows at {USER_BEHAVIOR_PATH}")
    print(f"Selected {len(selected.columns) - 1} behavioral features for clustering")
    print(segment_summary.to_string(index=False))


if __name__ == "__main__":
    main()
