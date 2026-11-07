"""Regression tests for read-only Hermes usage summaries."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from usage import summarize_agent, summarize_models


class OrbitalUsageTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "odin").mkdir()

    def create_database(self, records):
        path = self.root / "odin" / "state.db"
        db = sqlite3.connect(path)
        self.addCleanup(db.close)
        with db:
            db.execute("""
                CREATE TABLE session_model_usage (
                    api_call_count INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cache_read_tokens INTEGER,
                    cache_write_tokens INTEGER,
                    reasoning_tokens INTEGER,
                    estimated_cost_usd REAL,
                    cost_status TEXT,
                    last_seen TEXT,
                    first_seen TEXT,
                    model TEXT,
                    billing_provider TEXT,
                    billing_mode TEXT
                )
            """)
            db.executemany("""
                INSERT INTO session_model_usage
                (api_call_count, input_tokens, output_tokens,
                 cache_read_tokens, cache_write_tokens, reasoning_tokens,
                 estimated_cost_usd, cost_status, last_seen, first_seen,
                 model, billing_provider, billing_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [tuple(r) + (None,) * (13 - len(r)) for r in records])

    def test_missing_database(self):
        result = summarize_agent("odin", self.root)
        self.assertEqual(result["source_status"], "unavailable")
        self.assertIsNone(result["input_tokens"])
        self.assertIsNone(result["estimated_cost_usd"])

    def test_empty_usage_table(self):
        self.create_database([])
        result = summarize_agent("odin", self.root)
        self.assertEqual(result["source_status"], "available")
        self.assertEqual(result["usage_records"], 0)
        self.assertEqual(result["estimated_records"], 0)

    def test_cost_classifications(self):
        self.create_database([
            (2, 1000, 200, 300, 0, 10, 1.25, "estimated"),
            (1, 500, 100, 200, 0, 0, 0.00, "included"),
            (1, 250, 50, 0, 0, 0, 9.99, None),
        ])
        result = summarize_agent("odin", self.root)

        self.assertEqual(result["usage_records"], 3)
        self.assertEqual(result["estimated_records"], 1)
        self.assertEqual(result["included_records"], 1)
        self.assertEqual(result["unclassified_records"], 1)
        self.assertAlmostEqual(result["estimated_cost_usd"], 1.25)

    def test_token_aggregation(self):
        self.create_database([
            (2, 1000, 200, 300, 20, 10, 1.00, "estimated"),
            (3, 500, 100, 200, 30, 5, 0.00, "included"),
        ])
        result = summarize_agent("odin", self.root)

        self.assertEqual(result["api_calls"], 5)
        self.assertEqual(result["input_tokens"], 1500)
        self.assertEqual(result["output_tokens"], 300)
        self.assertEqual(result["cache_read_tokens"], 500)
        self.assertEqual(result["cache_write_tokens"], 50)
        self.assertEqual(result["reasoning_tokens"], 15)

    def test_period_filters_and_inclusive_boundary(self):
        now = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        self.create_database([
            (1, 100, 10, 0, 0, 0, 1.0, "estimated", "2026-11-01T10:00:00Z"),
            (1, 200, 20, 0, 0, 0, 2.0, "estimated", "2026-10-25T12:00:00Z"),
            (1, 300, 30, 0, 0, 0, 3.0, "estimated", "2026-10-10T12:00:00Z"),
            (1, 400, 40, 0, 0, 0, 4.0, "estimated", "2026-09-01T12:00:00Z"),
            (1, 500, 50, 0, 0, 0, 5.0, "estimated", None),
        ])
        today = summarize_agent("odin", self.root, "today", now)
        week = summarize_agent("odin", self.root, "7d", now)
        month = summarize_agent("odin", self.root, "30d", now)
        lifetime = summarize_agent("odin", self.root, "all", now)
        self.assertEqual([today["usage_records"], week["usage_records"],
                          month["usage_records"], lifetime["usage_records"]],
                         [1, 2, 3, 5])
        self.assertEqual(week["input_tokens"], 300)
        self.assertEqual(month["estimated_cost_usd"], 6.0)
        self.assertEqual(today["excluded_undated_records"], 1)
        self.assertEqual(lifetime["excluded_undated_records"], 0)

    def test_first_seen_fallback_and_future_exclusion(self):
        now = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        self.create_database([
            (1, 100, 0, 0, 0, 0, 0, "included", None, "2026-11-01T11:00:00Z"),
            (1, 200, 0, 0, 0, 0, 0, "included", "2026-11-02T11:00:00Z"),
        ])
        res = summarize_agent("odin", self.root, "today", now)
        self.assertEqual(res["usage_records"], 1)
        self.assertEqual(res["included_records"], 1)

    def test_invalid_period(self):
        with self.assertRaises(ValueError):
            summarize_agent("odin", self.root, "bad")

    def test_model_groups_match_agent_and_respect_dates(self):
        now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        self.create_database([
            (2, 100, 10, 5, 1, 2, 1.50, 'estimated', '2026-11-01T10:00:00Z', None, 'model-a', 'provider-x', 'api'),
            (1, 200, 20, 7, 2, 3, 8.00, None, '2026-11-01T09:00:00Z', None, 'model-a', 'provider-x', 'api'),
            (1, 300, 30, 9, 3, 4, 0.00, 'included', '2026-10-01T10:00:00Z', None, 'model-b', 'provider-y', 'subscription'),
            (1, 400, 40, 0, 0, 0, 2.00, 'estimated', None, None, 'model-c', 'provider-x', 'api'),
        ])
        groups = summarize_models('odin', self.root, 'today', now)
        self.assertEqual(len(groups), 1)
        row = groups[0]
        self.assertEqual((row['model'], row['provider'], row['billing_mode']), ('model-a', 'provider-x', 'api'))
        self.assertEqual(row['usage_records'], 2)
        self.assertEqual(row['api_calls'], 3)
        self.assertEqual(row['input_tokens'], 300)
        self.assertEqual(row['estimated_cost_usd'], 1.50)
        self.assertEqual((row['estimated_records'], row['included_records'], row['unclassified_records']), (1, 0, 1))
        all_rows = summarize_models('odin', self.root, 'all', now)
        self.assertEqual(sum(r['usage_records'] for r in all_rows), 4)
        self.assertEqual(sum(r['input_tokens'] for r in all_rows), summarize_agent('odin', self.root, 'all', now)['input_tokens'])
        self.assertEqual(sum(r['estimated_cost_usd'] for r in all_rows), 3.50)

    def test_model_missing_database_and_invalid_period(self):
        self.assertEqual(summarize_models('odin', self.root), [])
        with self.assertRaises(ValueError):
            summarize_models('odin', self.root, 'invalid')
        with self.assertRaises(ValueError):
            summarize_models('../unknown', self.root)

    def test_reject_unknown_agent(self):
        with self.assertRaises(ValueError):
            summarize_agent("../unknown", self.root)


if __name__ == "__main__":
    unittest.main()
