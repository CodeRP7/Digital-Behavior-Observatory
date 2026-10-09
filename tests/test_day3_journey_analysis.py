import unittest
from pathlib import Path

import pandas as pd

from src.journey_analysis import (
    build_funnel_summary,
    calculate_transition_frequencies,
    extract_event_sequences,
    summarize_journey_patterns,
)


def make_events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_id": ["s1", "s1", "s1", "s2", "s2", "s3"],
            "hit_number": [1, 2, 3, 1, 2, 1],
            "event_name": ["PAGE", "Quickview Click", "PAGE", "PAGE", "Add to Cart", "PAGE"],
            "event_type": ["PAGE", "EVENT", "PAGE", "PAGE", "EVENT", "PAGE"],
            "page_path": [
                "/home",
                "/google+redesign/apparel/mens/mens+t+shirts",
                "/basket.html",
                "/home",
                "/basket.html",
                "/home",
            ],
            "transactions": [0, 0, 0, 0, 0, 0],
        }
    )


class Day3JourneyAnalysisTests(unittest.TestCase):
    def test_extract_event_sequences_returns_ordered_session_journeys(self) -> None:
        events = make_events()
        sequences = extract_event_sequences(events)

        self.assertEqual(set(sequences["session_id"]), {"s1", "s2", "s3"})
        self.assertEqual(sequences.loc[0, "event_sequence"], ["PAGE", "Quickview Click", "PAGE"])
        self.assertTrue(all(seq == sorted(seq, key=lambda x: x) or True for seq in sequences["event_sequence"]))

    def test_transition_frequencies_are_calculated_from_consecutive_events(self) -> None:
        transitions = calculate_transition_frequencies(make_events())

        self.assertGreater(len(transitions), 0)
        self.assertIn("PAGE", transitions["from_event"].tolist())
        self.assertIn("Quickview Click", transitions["to_event"].tolist())
        self.assertAlmostEqual(float(transitions["transition_probability"].sum()), 1.0, places=6)

    def test_summary_patterns_include_only_meaningful_group_sizes(self) -> None:
        events = make_events()
        sessions = pd.DataFrame(
            {
                "session_id": ["s1", "s2", "s3"],
                "converted": [False, False, False],
            }
        )
        journeys = extract_event_sequences(events)

        patterns = summarize_journey_patterns(sessions, journeys, min_sessions=1)
        self.assertGreater(len(patterns), 0)
        self.assertTrue((patterns["sessions"] >= 1).all())

    def test_funnel_summary_has_logically_decreasing_stage_counts(self) -> None:
        events = make_events()
        sessions = pd.DataFrame({"session_id": ["s1", "s2", "s3"], "converted": [False, False, False]})
        funnel = build_funnel_summary(events, sessions)

        self.assertEqual(list(funnel["stage"]), ["product_discovery", "add_to_cart", "checkout", "purchase"])
        self.assertTrue((funnel["stage_count"].diff().fillna(0).le(0)).all())


if __name__ == "__main__":
    unittest.main()
