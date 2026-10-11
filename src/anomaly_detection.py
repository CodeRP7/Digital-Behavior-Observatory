"""Session-level anomaly detection using behavioral features already built in the project."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SESSION_FEATURES_PATH = PROCESSED_DIR / "session_features.csv"
ANOMALY_SCORE_PATH = PROCESSED_DIR / "session_anomaly_scores.csv"
ANOMALY_SUMMARY_PATH = PROCESSED_DIR / "session_anomaly_summary.csv"

DEFAULT_FEATURE_COLUMNS = [
    "session_duration_seconds",
    "event_count",
    "navigation_depth",
    "unique_action_count",
    "repeated_action_count",
    "events_per_minute",
]

FEATURE_DESCRIPTIONS = {
    "session_duration_seconds": "Total length of the session; extreme values indicate unusually long or short browsing behavior.",
    "event_count": "Number of hits in the session; very high values indicate unusually intense interaction.",
    "navigation_depth": "Total page hits in the session; unusually deep navigation suggests unusual browsing volume.",
    "unique_action_count": "Distinct events/actions observed; unusual action diversity signals different behavior patterns.",
    "repeated_action_count": "Count of repeated actions beyond the first occurrence; a high value can indicate repetitive or automated behavior.",
    "events_per_minute": "Session event rate; very high rates suggest compressed or unusually intense browsing bursts.",
}


def build_anomaly_feature_matrix(
    session_features: pd.DataFrame,
    feature_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Return the session-level behavior matrix for anomaly identification."""
    if session_features is None or session_features.empty:
        raise ValueError("Session feature table is empty; cannot detect anomalies.")

    if feature_columns is None:
        feature_columns = DEFAULT_FEATURE_COLUMNS

    missing = [column for column in feature_columns if column not in session_features.columns]
    if missing:
        raise ValueError(
            "The following anomaly feature columns are missing: " + ", ".join(missing)
        )

    matrix = session_features[["session_id", "user_id", *feature_columns]].copy()
    for column in feature_columns:
        matrix[column] = pd.to_numeric(matrix[column], errors="coerce").fillna(0.0)
    return matrix


compute_anomaly_features = build_anomaly_feature_matrix


def summarize_feature_distributions(session_features: pd.DataFrame) -> pd.DataFrame:
    """Summarize skew and range so anomaly thresholds are grounded in observed behavior."""
    matrix = build_anomaly_feature_matrix(session_features)
    numeric = matrix.drop(columns=["session_id", "user_id"])
    summary = (
        numeric.agg(
            ["mean", "median", "std", "min", "max", "quantile_01", "quantile_05", "quantile_95", "quantile_99"]
        )
        .T
    )
    summary["iqr"] = summary["quantile_95"] - summary["quantile_05"]
    return summary.round(4)


def compute_robust_z_scores(session_features: pd.DataFrame) -> pd.DataFrame:
    """Compute a robust z-score for each candidate anomaly feature."""
    matrix = build_anomaly_feature_matrix(session_features)
    result = matrix[["session_id", "user_id"]].copy()
    for column in DEFAULT_FEATURE_COLUMNS:
        values = matrix[column].to_numpy(dtype=float)
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        robust_score = np.zeros_like(values, dtype=float)
        if mad != 0:
            robust_score = 0.6745 * (values - median) / mad
        result[f"{column}_robust_z"] = robust_score
    return result


def fit_isolation_forest(
    session_features: pd.DataFrame,
    contamination: float = 0.02,
    random_state: int = 42,
    feature_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, object]:
    """Fit Isolation Forest for session-level anomaly detection.

    The contamination parameter is set to 2% because the dataset has 2,556 sessions and the
    observed behavioral tails are strongly skewed. This assumption treats roughly 50 sessions as
    sufficiently rare to warrant investigation without labeling the whole tail as malicious.
    """
    matrix = build_anomaly_feature_matrix(session_features, feature_columns=feature_columns)
    feature_columns = list(matrix.columns.difference(["session_id", "user_id"]))
    X = matrix[feature_columns].copy()
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)

    scaler = RobustScaler()
    scaled = scaler.fit_transform(X)

    model = IsolationForest(
        contamination=contamination,
        n_estimators=300,
        random_state=random_state,
    )
    labels = model.fit_predict(scaled)
    decision = model.decision_function(scaled)
    decision_min = float(decision.min())
    decision_max = float(decision.max())
    if decision_max == decision_min:
        anomaly_score = np.zeros(len(matrix), dtype=float)
    else:
        anomaly_score = (decision_max - decision) / (decision_max - decision_min)

    output = matrix[["session_id", "user_id"]].copy()
    output["anomaly_label"] = np.where(labels == -1, "anomaly", "normal")
    output["anomaly_score"] = anomaly_score.astype(float)
    output["isolation_decision"] = decision.astype(float)
    output["feature_count_flagged"] = 0

    robust_z = compute_robust_z_scores(session_features)
    score_columns = [column for column in robust_z.columns if column.endswith("_robust_z")]
    output = output.merge(robust_z, on=["session_id", "user_id"], how="left")
    output["feature_count_flagged"] = (
        output[score_columns].abs().gt(3.5).sum(axis=1)
    )
    output["robust_z_max"] = output[score_columns].abs().max(axis=1)

    output["anomaly_score"] = output["anomaly_score"].clip(0.0, 1.0)
    output["anomaly_rank"] = output["anomaly_score"].rank(method="first", ascending=False).astype(int)
    return output.sort_values("anomaly_score", ascending=False).reset_index(drop=True), model


def identify_statistical_anomalies(session_features: pd.DataFrame) -> pd.DataFrame:
    """Add a simple robust-statistical anomaly flag for a secondary check."""
    matrix = build_anomaly_feature_matrix(session_features)
    robust = compute_robust_z_scores(session_features)
    anomaly_flags = matrix[["session_id", "user_id"]].copy()
    anomaly_flags["robust_z_max"] = robust[[column for column in robust.columns if column.endswith("_robust_z")]].abs().max(axis=1)
    anomaly_flags["statistical_outlier"] = anomaly_flags["robust_z_max"].gt(3.5)
    return anomaly_flags


def build_anomaly_summary(session_anomalies: pd.DataFrame) -> pd.DataFrame:
    """Summarize behavior by anomaly status for interpretation and reporting."""
    if "anomaly_label" not in session_anomalies.columns:
        raise ValueError("Session anomaly table does not include an anomaly label column.")

    summary_cols = [
        "session_duration_seconds",
        "event_count",
        "navigation_depth",
        "unique_action_count",
        "repeated_action_count",
        "events_per_minute",
    ]
    present = [column for column in summary_cols if column in session_anomalies.columns]
    grouped = session_anomalies.groupby("anomaly_label", dropna=False)
    summary = grouped[["anomaly_score", *present]].mean().reset_index()
    summary["anomaly_count"] = grouped.size().values
    return summary.sort_values(["anomaly_count", "anomaly_score"], ascending=[False, False]).reset_index(drop=True)


def main() -> None:
    if not SESSION_FEATURES_PATH.exists():
        raise FileNotFoundError(
            "Session feature table not found. Run `python -m src.preprocessing` and `python -m src.session_builder` first."
        )

    session_features = pd.read_csv(
        SESSION_FEATURES_PATH,
        dtype={"session_id": "string", "user_id": "string"},
    )
    if "session_start" in session_features.columns:
        session_features["session_start"] = pd.to_datetime(
            session_features["session_start"], format="ISO8601", utc=True, errors="raise"
        )
    if "session_end" in session_features.columns:
        session_features["session_end"] = pd.to_datetime(
            session_features["session_end"], format="ISO8601", utc=True, errors="raise"
        )

    feature_matrix = build_anomaly_feature_matrix(session_features)
    anomaly_scores, _ = fit_isolation_forest(session_features, contamination=0.02)
    statistical_flags = identify_statistical_anomalies(session_features)

    output = feature_matrix[["session_id", "user_id"]].merge(
        anomaly_scores, on=["session_id", "user_id"], how="left"
    )
    output = output.merge(
        statistical_flags.rename(columns={"robust_z_max": "robust_z_max_statistical"}),
        on=["session_id", "user_id"],
        how="left",
    )
    output["robust_z_max"] = output["robust_z_max"].combine_first(
        output["robust_z_max_statistical"]
    )
    output = output.drop(columns=["robust_z_max_statistical"])
    output["anomaly_label"] = output["anomaly_label"].fillna("normal")

    summary = build_anomaly_summary(output)
    summary["method"] = "Isolation Forest + robust z-score"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(ANOMALY_SCORE_PATH, index=False)
    summary.to_csv(ANOMALY_SUMMARY_PATH, index=False)

    reported = output[output["anomaly_label"] == "anomaly"].sort_values("anomaly_score", ascending=False)
    print(f"Scored {len(output):,} sessions for anomaly detection")
    print(f"Isolation Forest flagged {len(reported):,} anomalous sessions")
    print(summary.to_string(index=False))
    if not reported.empty:
        print("Top anomalies:")
        top_columns = [
            "session_id",
            "user_id",
            "anomaly_score",
            "robust_z_max",
            "feature_count_flagged",
        ]
        print(reported[top_columns].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
