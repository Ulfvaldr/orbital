"""Phase 3 operation metrics, independent of Hermes live database."""
import unittest
from datetime import datetime, timezone
from operations import summarize_operations, timestamp

NOW = datetime(2026, 11, 7, 13, tzinfo=timezone.utc)
class OperationsTests(unittest.TestCase):
    def test_task_statuses_and_deduplicated_runs(self):
        tasks = [
            {'id':'a','assignee':'odin','status':'completed','completed_at':'2026-11-07T12:00:00Z'},
            {'id':'b','assignee':'bao','status':'failed','completed_at':'2026-11-06T08:00:00Z'},
            {'id':'c','assignee':'brokkr','status':'running'},
            {'id':'d','assignee':'veritas','status':'unknown'},
            {'id':'e','assignee':'external','status':'completed','completed_at':'2026-11-07T11:00:00Z'},
        ]
        p=summarize_operations(tasks,[{'task_id':'a'},{'task_id':'a'}],7,NOW)
        self.assertEqual(p['totals']['tasks'],4)
        self.assertEqual(p['totals']['completed'],1)
        self.assertEqual(p['totals']['failed'],1)
        self.assertEqual(p['totals']['active_or_pending'],1)
        self.assertEqual(p['totals']['other'],1)
        self.assertEqual(p['totals']['completion_rate_pct'],50)
        self.assertEqual(sum(d['completed'] for d in p['timeline']),1)
        self.assertEqual(sum(d['failed'] for d in p['timeline']),1)
        self.assertEqual(p['coverage']['unassigned_or_other_assignee_tasks'],1)
    def test_missing_completion_date_not_fabricated(self):
        p=summarize_operations([{'assignee':'Odin','status':'done','updated_at':'2026-11-07T12:00:00Z'}],[],14,NOW)
        self.assertEqual(p['totals']['completed'],1)
        self.assertEqual(sum(d['completed'] for d in p['timeline']),0)
        self.assertEqual(p['coverage']['terminal_tasks_missing_completed_at'],1)
    def test_utc_boundary_and_future(self):
        tasks=[{'assignee':'odin','status':'completed','completed_at':'2026-11-01T23:59:59Z'},
               {'assignee':'odin','status':'completed','completed_at':'2026-11-07T14:00:00Z'},
               {'assignee':'odin','status':'completed','completed_at':'2026-10-31T23:59:59Z'}]
        p=summarize_operations(tasks,[],7,NOW)
        self.assertEqual(sum(d['completed'] for d in p['timeline']),1)
    def test_invalid_window_and_timestamp(self):
        with self.assertRaises(ValueError):summarize_operations([],[],60,NOW)
        self.assertIsNone(timestamp('2026-11-07 13:00:00'))
        self.assertIsNone(timestamp('garbage'))
        self.assertIsNone(timestamp(float('nan')))
    def test_unavailable_flag(self):
        p=summarize_operations([],[],14,NOW,source_available=False)
        self.assertEqual(p['source_status'],'unavailable')
        self.assertIsNone(p['totals']['completion_rate_pct'])

if __name__ == '__main__':unittest.main()
