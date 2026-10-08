import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.preprocessing import clean_events, write_quality_report
from src.session_builder import build_session_features


def make_raw_events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": ["user-1", "user-1", "user-2"],
            "source_session_id": ["shared", "shared", "shared"],
            "event_date": [20170801, 20170801, 20170801],
            "session_start_epoch": [1501570840, 1501570840, 1501570840],
            "hit_number": [1, 2, 1],
            "event_type": ["PAGE", "EVENT", "PAGE"],
            "page_path": ["/home", "/home", "/home"],
            "event_category": [None, " Cart ", None],
            "event_action": [None, " Add ", None],
            "event_label": [None, None, None],
            "hit_time_ms": [0, 1000, 0],
            "device_type": ["desktop", "desktop", "mobile"],
            "platform": ["Windows", "Windows", "Android"],
            "browser": ["Chrome", "Chrome", "Chrome"],
            "transactions": [None, None, 1],
        }
    )


class Day2PipelineTests(unittest.TestCase):
    def test_cleaning_and_sessionization_use_composite_keys(self) -> None:
        raw = make_raw_events()
        original = raw.copy(deep=True)

        cleaned, invalid_records, duplicates_removed = clean_events(raw)
        sessions = build_session_features(cleaned)

        self.assertTrue(raw.equals(original))
        self.assertEqual(invalid_records, 0)
        self.assertEqual(duplicates_removed, 0)
        self.assertEqual(cleaned["session_id"].nunique(), 2)
        self.assertEqual(sessions["session_id"].nunique(), 2)
        self.assertEqual(sessions["event_count"].sum(), len(cleaned))
        self.assertEqual(sessions["user_id"].nunique(), 2)
        self.assertTrue(sessions["session_duration_seconds"].ge(0).all())
        self.assertEqual(int(sessions["converted"].sum()), 1)
        self.assertEqual(
            cleaned.loc[cleaned["event_type"] == "EVENT", "event_action"].iloc[0],
            "Add",
        )
        self.assertTrue(cleaned["event_timestamp"].notna().all())

    def test_invalid_and_exact_duplicate_rows_are_counted(self) -> None:
        raw = make_raw_events()
        raw = pd.concat(
            [
                raw,
                raw.iloc[[0]],
                pd.DataFrame([{**raw.iloc[0].to_dict(), "event_type": None}]),
                pd.DataFrame([{**raw.iloc[1].to_dict(), "hit_number": 1.5}]),
                pd.DataFrame([{**raw.iloc[2].to_dict(), "transactions": 1.5}]),
            ],
            ignore_index=True,
        )

        cleaned, invalid_records, duplicates_removed = clean_events(raw)

        self.assertEqual(invalid_records, 3)
        self.assertEqual(duplicates_removed, 1)
        self.assertEqual(len(cleaned), 3)

    def test_session_attribute_conflicts_are_rejected(self) -> None:
        cleaned, _, _ = clean_events(make_raw_events())
        cleaned.loc[1, "device_type"] = "mobile"

        with self.assertRaisesRegex(ValueError, "conflicting device_type"):
            build_session_features(cleaned)

    def test_quality_report_is_written_separately_from_raw_input(self) -> None:
        raw = make_raw_events()
        cleaned, invalid_records, duplicates_removed = clean_events(raw)
        sessions = build_session_features(cleaned)
        audit = {
            "missing": raw.isna().sum().to_dict(),
            "dtypes": raw.dtypes.astype(str).to_dict(),
            "cardinality": {"event_type": 2},
            "source_session_ids_shared_by_users": 1,
            "source_event_date_range": ("2017-08-01", "2017-08-01"),
            "session_start_utc_range": (
                "2017-08-01T07:00:40+00:00",
                "2017-08-01T07:00:40+00:00",
            ),
            "duplicate_rows": 0,
            "invalid_session_start_timestamps": 0,
            "invalid_source_event_dates": 0,
            "hit_number_range": (1, 2),
            "hit_time_ms_range": (0, 1000),
            "transactions_range": (1, 1),
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "raw.csv"
            report_path = root / "reports" / "quality.md"
            source_path.write_text("raw input stays unchanged", encoding="utf-8")
            write_quality_report(
                source_path,
                report_path,
                raw,
                cleaned,
                sessions,
                audit,
                invalid_records,
                duplicates_removed,
            )

            self.assertEqual(
                source_path.read_text(encoding="utf-8"), "raw input stays unchanged"
            )
            self.assertIn("Rows before cleaning: 3", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
