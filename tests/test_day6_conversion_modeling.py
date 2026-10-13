import unittest

import pandas as pd

from src.modeling import build_modeling_dataset, compare_models, get_feature_leakage_audit


class Day6ConversionModelingTests(unittest.TestCase):
    def test_modeling_dataset_uses_session_as_entity_and_excludes_target_leakage(self) -> None:
        session_features = pd.read_csv(
            "data/processed/session_features.csv",
            dtype={"user_id": "string", "session_id": "string"},
        )
        user_behavior = pd.read_csv(
            "data/processed/user_behavior_features.csv",
            dtype={"user_id": "string"},
        )

        modeling_table = build_modeling_dataset(session_features, user_behavior)

        self.assertIn("entity_id", modeling_table.columns)
        self.assertIn("target", modeling_table.columns)
        self.assertNotIn("transaction_count", modeling_table.columns)
        self.assertNotIn("converted", modeling_table.columns)
        self.assertEqual(modeling_table["target"].dtype.kind, "i")
        self.assertGreater(len(modeling_table), 0)

    def test_leakage_audit_explicitly_excludes_target_and_identifiers(self) -> None:
        audit = get_feature_leakage_audit()

        self.assertIn("transaction_count", audit["feature"].tolist())
        self.assertIn("converted", audit["feature"].tolist())
        self.assertFalse(bool(audit.loc[audit["feature"] == "transaction_count", "included"].iloc[0]))
        self.assertFalse(bool(audit.loc[audit["feature"] == "converted", "included"].iloc[0]))

    def test_model_comparison_returns_ranked_results(self) -> None:
        session_features = pd.read_csv(
            "data/processed/session_features.csv",
            dtype={"user_id": "string", "session_id": "string"},
        )
        user_behavior = pd.read_csv(
            "data/processed/user_behavior_features.csv",
            dtype={"user_id": "string"},
        )

        modeling_table = build_modeling_dataset(session_features, user_behavior)
        comparison, artifact = compare_models(modeling_table)

        self.assertGreater(len(comparison), 0)
        self.assertIn("model", comparison.columns)
        self.assertIn("best_model_name", artifact)
        self.assertTrue(artifact["best_model_name"])


if __name__ == "__main__":
    unittest.main()
