"""Conversion prediction pipeline for the Digital Behavior Observatory data."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
SESSION_FEATURES_PATH = PROCESSED_DIR / "session_features.csv"
USER_FEATURES_PATH = PROCESSED_DIR / "user_behavior_features.csv"
TARGET_COLUMN = "converted"
ENTITY_COLUMN = "session_id"


def _resolve_data_path(path: Path | str) -> Path:
    """Resolve a dataset path relative to the repo root when a notebook/kernel runs from a subdirectory."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    repo_candidate = PROJECT_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate

    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    return repo_candidate

LEAKAGE_AUDIT = [
    {
        "feature": "session_id",
        "included": False,
        "reason": "Unique session identifier is an entity ID, not a behavioral signal.",
    },
    {
        "feature": "user_id",
        "included": False,
        "reason": "User ID is not a causal feature and would leak user-level information into a prospective session score.",
    },
    {
        "feature": "source_session_id",
        "included": False,
        "reason": "This is the source session identifier, not a behavioral measure.",
    },
    {
        "feature": "transaction_count",
        "included": False,
        "reason": "This is the direct conversion metric and would create target leakage.",
    },
    {
        "feature": "converted",
        "included": False,
        "reason": "This is the prediction target; it must not be used as a feature.",
    },
    {
        "feature": "session_start",
        "included": False,
        "reason": "Start timestamp is metadata and not behaviorally interpretable without a temporal baseline; we use hour and time_of_day instead.",
    },
    {
        "feature": "session_end",
        "included": False,
        "reason": "The session end timestamp is not available before the conversion decision and can encode the outcome window.",
    },
    {
        "feature": "session_date",
        "included": False,
        "reason": "This reflects the same sample window and can leak a single-day pattern into the model.",
    },
    {
        "feature": "week",
        "included": False,
        "reason": "Calendar buckets are not behavioral drivers and are not stable beyond the single export window.",
    },
    {
        "feature": "month",
        "included": False,
        "reason": "Month level is a sampling artifact rather than a conversion signal.",
    },
    {
        "feature": "first_event",
        "included": False,
        "reason": "This is too specific to individual sessions and can drift with event taxonomy rather than core behavior.",
    },
    {
        "feature": "last_event",
        "included": False,
        "reason": "It is a post-observation summary and is not available before the user finishes the session.",
    },
    {
        "feature": "entry_page",
        "included": True,
        "reason": "Entry page can signal commercial intent when it is a product or category page; it is retained only in the restricted, interpretable model subset.",
    },
    {
        "feature": "exit_page",
        "included": True,
        "reason": "Exit page may be informative of browsing completion and is observed within-session before the conversion decision.",
    },
    {
        "feature": "event_count",
        "included": True,
        "reason": "This is behavior volume within the session and is available before the outcome is known.",
    },
    {
        "feature": "navigation_depth",
        "included": True,
        "reason": "Depth of browsing indicates product exploration and is measured before conversion completion.",
    },
    {
        "feature": "unique_action_count",
        "included": True,
        "reason": "Interaction diversity reflects action intent and remains a session-level behavioral signal.",
    },
    {
        "feature": "repeated_action_count",
        "included": True,
        "reason": "Repeat interactions may reveal habit or friction; it is derived within the session before the outcome is observed.",
    },
    {
        "feature": "session_duration_seconds",
        "included": True,
        "reason": "Duration is an observable behavioral measure recorded during the session and does not encode the final transaction outcome.",
    },
    {
        "feature": "events_per_minute",
        "included": True,
        "reason": "Rate of activity captures engagement intensity while the session is still active.",
    },
    {
        "feature": "device_type",
        "included": True,
        "reason": "Device context is available before the session ends and is a stable behavioral/environmental signal.",
    },
    {
        "feature": "platform",
        "included": True,
        "reason": "Platform is collected at session start and helps explain conversion propensity without using the outcome itself.",
    },
    {
        "feature": "browser",
        "included": True,
        "reason": "Browser is a stable session context variable and not a downstream transaction metric.",
    },
    {
        "feature": "time_of_day",
        "included": True,
        "reason": "Hourly behavior context is available before the conversion outcome and reflects traffic timing patterns.",
    },
    {
        "feature": "return_frequency",
        "included": True,
        "reason": "This user-level behavioral signal comes from prior interaction history and is permissible when used as a pre-session context feature.",
    },
    {
        "feature": "sessions_per_user",
        "included": True,
        "reason": "It measures prior repeat use and is available before modeling a current session outcome.",
    },
]


def load_session_features(path: Path | str = SESSION_FEATURES_PATH) -> pd.DataFrame:
    """Read the processed session feature table."""
    resolved_path = _resolve_data_path(path)
    dataframe = pd.read_csv(resolved_path, dtype={"user_id": "string", "session_id": "string"})
    for column in ("session_start", "session_end", "session_date"):
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
    return dataframe


def load_user_behavior(path: Path | str = USER_FEATURES_PATH) -> pd.DataFrame:
    """Read the user-level behavior table generated during Day 4."""
    resolved_path = _resolve_data_path(path)
    dataframe = pd.read_csv(resolved_path, dtype={"user_id": "string"})
    for column in ("first_seen", "last_seen"):
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
    return dataframe


def get_feature_leakage_audit() -> pd.DataFrame:
    """Return a structured file-friendly leakage review."""
    return pd.DataFrame(LEAKAGE_AUDIT)


def build_modeling_dataset(
    session_features: pd.DataFrame,
    user_behavior: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Construct a session-level conversion dataset with behavioral and context features."""
    if session_features is None or session_features.empty:
        raise ValueError("Session feature table is empty; cannot build the conversion dataset.")

    working = session_features.copy()
    working[ENTITY_COLUMN] = working[ENTITY_COLUMN].astype("string")
    working["converted"] = working["converted"].astype(bool).astype(int)

    if user_behavior is not None and not user_behavior.empty:
        behavior_subset = [
            "user_id",
            "session_count",
            "avg_session_duration_seconds",
            "events_per_session",
            "avg_navigation_depth",
            "avg_unique_event_count",
            "return_frequency",
            "repeated_action_frequency",
        ]
        available = [column for column in behavior_subset if column in user_behavior.columns]
        history = user_behavior[available].copy()
        history["user_id"] = history["user_id"].astype("string")
        working = working.merge(history, on="user_id", how="left", suffixes=("", "_history"))

    target = "converted"
    excluded = {
        "user_id",
        "source_session_id",
        "session_start",
        "session_end",
        "session_date",
        "week",
        "month",
        "transaction_count",
        "first_event",
        "last_event",
        TARGET_COLUMN,
    }

    feature_columns = [
        column for column in working.columns if column not in {ENTITY_COLUMN, "user_id", target, *excluded}
    ]

    selected = [ENTITY_COLUMN, *feature_columns, target]
    dataset = working[selected].copy()
    dataset = dataset.rename(columns={ENTITY_COLUMN: "entity_id"})
    dataset = dataset.rename(columns={target: "target"})

    numeric_columns = [
        column for column in dataset.columns if column not in {"entity_id", "target"} and pd.api.types.is_numeric_dtype(dataset[column])
    ]
    for column in numeric_columns:
        dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
    dataset[numeric_columns] = dataset[numeric_columns].fillna(0.0)

    categorical_columns = [
        column for column in dataset.columns if column not in {"entity_id", "target"} and column not in numeric_columns
    ]
    for column in categorical_columns:
        dataset[column] = dataset[column].fillna("unknown").astype(str)

    dataset = dataset.reset_index(drop=True)
    dataset["target"] = dataset["target"].astype(int)
    return dataset


def _build_preprocessor(modeling_dataset: pd.DataFrame) -> ColumnTransformer:
    numeric_columns = [
        column
        for column in modeling_dataset.columns
        if column not in {"entity_id", "target"} and pd.api.types.is_numeric_dtype(modeling_dataset[column])
    ]
    categorical_columns = [
        column
        for column in modeling_dataset.columns
        if column not in {"entity_id", "target"} and column not in numeric_columns
    ]

    transformers = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
                categorical_columns,
            )
        )
    if not transformers:
        raise ValueError("No feature columns remain in the model matrix after filtering.")
    return ColumnTransformer(transformers=transformers, remainder="drop")


def _select_threshold(probabilities: np.ndarray, labels: pd.Series) -> float:
    precision, recall, thresholds = pd.Series(np.array([])), pd.Series(np.array([])), np.array([])
    from sklearn.metrics import precision_recall_curve

    p, r, t = precision_recall_curve(labels, probabilities)
    if len(t) == 0:
        return 0.5
    f1 = 2 * p[:-1] * r[:-1] / (p[:-1] + r[:-1] + 1e-12)
    best_index = int(np.nanargmax(f1))
    return float(t[best_index])


def compare_models(modeling_dataset: pd.DataFrame, random_state: int = 42) -> tuple[pd.DataFrame, dict[str, object]]:
    """Train a few defensible classifiers and compare them on a validation/test split."""
    if modeling_dataset is None or modeling_dataset.empty:
        raise ValueError("Modeling dataset is empty; cannot compare models.")
    if "target" not in modeling_dataset.columns:
        raise ValueError("Modeling dataset must include a target column named 'target'.")

    feature_columns = [
        column for column in modeling_dataset.columns if column not in {"entity_id", "target"}
    ]
    if not feature_columns:
        raise ValueError("No feature columns remain after building the modeling table.")

    X = modeling_dataset[feature_columns].copy()
    y = modeling_dataset["target"].astype(int)

    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=0.40,
        stratify=y,
        random_state=random_state,
    )
    X_valid, X_test, y_valid, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.50,
        stratify=y_temp,
        random_state=random_state,
    )

    estimators = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_state),
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=random_state,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_depth=6,
            learning_rate=0.05,
            max_iter=200,
            random_state=random_state,
        ),
    }

    comparison_rows: list[dict[str, object]] = []
    best_model = None
    best_model_name = ""
    best_threshold = 0.5
    best_validation_pr = -1.0
    best_test_probabilities = None
    best_test_predictions = None

    for name, estimator in estimators.items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", _build_preprocessor(pd.concat([X_train, X_valid], axis=0).reset_index(drop=True))),
                ("model", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)

        validation_probabilities = pipeline.predict_proba(X_valid)[:, 1]
        validation_threshold = _select_threshold(validation_probabilities, y_valid)
        validation_predictions = (validation_probabilities >= validation_threshold).astype(int)

        valid_auc = roc_auc_score(y_valid, validation_probabilities)
        valid_pr = average_precision_score(y_valid, validation_probabilities)
        valid_f1 = f1_score(y_valid, validation_predictions, zero_division=0)
        valid_precision = precision_score(y_valid, validation_predictions, zero_division=0)
        valid_recall = recall_score(y_valid, validation_predictions, zero_division=0)
        valid_balanced_accuracy = balanced_accuracy_score(y_valid, validation_predictions)

        test_probabilities = pipeline.predict_proba(X_test)[:, 1]
        test_predictions = (test_probabilities >= validation_threshold).astype(int)
        test_auc = roc_auc_score(y_test, test_probabilities)
        test_pr = average_precision_score(y_test, test_probabilities)
        test_f1 = f1_score(y_test, test_predictions, zero_division=0)
        test_precision = precision_score(y_test, test_predictions, zero_division=0)
        test_recall = recall_score(y_test, test_predictions, zero_division=0)
        test_balanced_accuracy = balanced_accuracy_score(y_test, test_predictions)

        row = {
            "model": name,
            "validation_threshold": validation_threshold,
            "validation_roc_auc": valid_auc,
            "validation_average_precision": valid_pr,
            "validation_f1": valid_f1,
            "validation_precision": valid_precision,
            "validation_recall": valid_recall,
            "validation_balanced_accuracy": valid_balanced_accuracy,
            "test_roc_auc": test_auc,
            "test_average_precision": test_pr,
            "test_f1": test_f1,
            "test_precision": test_precision,
            "test_recall": test_recall,
            "test_balanced_accuracy": test_balanced_accuracy,
        }
        comparison_rows.append(row)

        if valid_pr > best_validation_pr:
            best_model = pipeline
            best_model_name = name
            best_threshold = validation_threshold
            best_validation_pr = valid_pr
            best_test_probabilities = test_probabilities
            best_test_predictions = test_predictions

    comparison = pd.DataFrame(comparison_rows).sort_values(
        by=["validation_average_precision", "validation_roc_auc"], ascending=False
    ).reset_index(drop=True)

    artifact = {
        "feature_columns": feature_columns,
        "best_model_name": best_model_name,
        "best_threshold": best_threshold,
        "best_model": best_model,
        "best_validation_pr_auc": best_validation_pr,
        "best_test_probabilities": best_test_probabilities,
        "best_test_predictions": best_test_predictions,
        "test_labels": y_test,
        "test_entity_ids": modeling_dataset.loc[X_test.index, "entity_id"].to_numpy(),
    }
    return comparison, artifact


def save_best_model(best_model: object, destination: Path | str = MODELS_DIR / "best_conversion_model.pkl") -> Path:
    """Persist the winning model to the repo models directory."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as file_handle:
        pickle.dump(best_model, file_handle)
    return destination


def build_error_analysis(
    modeling_dataset: pd.DataFrame,
    best_model: object,
    threshold: float,
    random_state: int = 42,
) -> pd.DataFrame:
    """Summarize false positives and false negatives for the best model."""
    if modeling_dataset is None or modeling_dataset.empty:
        raise ValueError("Modeling dataset is empty; cannot analyze prediction errors.")

    feature_columns = [
        column for column in modeling_dataset.columns if column not in {"entity_id", "target"}
    ]
    X = modeling_dataset[feature_columns]
    y_true = modeling_dataset["target"].astype(int)
    probabilities = best_model.predict_proba(X)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    errors = modeling_dataset[["entity_id", "target"]].copy()
    errors["predicted_probability"] = probabilities
    errors["predicted_label"] = predictions
    errors["is_error"] = errors["target"] != predictions
    errors["error_type"] = np.where(
        errors["target"].eq(1) & errors["predicted_label"].eq(0),
        "false_negative",
        np.where(errors["target"].eq(0) & errors["predicted_label"].eq(1), "false_positive", "correct"),
    )
    return errors[errors["is_error"] == 1].sort_values(
        by=["error_type", "predicted_probability"], ascending=[True, False]
    )


def main() -> None:
    """Create the reusable conversion modeling dataset and comparison report."""
    session_features = load_session_features(SESSION_FEATURES_PATH)
    user_behavior = load_user_behavior(USER_FEATURES_PATH)
    modeling_table = build_modeling_dataset(session_features, user_behavior)

    comparison, artifact = compare_models(modeling_table)
    best_model = artifact["best_model"]
    if best_model is None:
        raise RuntimeError("No model produced a valid validation result.")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    modeling_table.to_csv(PROCESSED_DIR / "conversion_modeling_table.csv", index=False)
    comparison.to_csv(PROCESSED_DIR / "conversion_model_comparison.csv", index=False)
    error_table = build_error_analysis(
        modeling_table,
        best_model,
        float(artifact["best_threshold"]),
    )
    error_table.to_csv(PROCESSED_DIR / "conversion_model_errors.csv", index=False)
    save_best_model(best_model, MODELS_DIR / "best_conversion_model.pkl")

    print(f"Built modeling table with {len(modeling_table):,} sessions and {modeling_table['target'].mean():.4f} conversion rate.")
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
