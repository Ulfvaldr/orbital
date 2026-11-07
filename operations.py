"""Pure, read-only operational summaries of Hermes task records."""
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import math

AGENTS = ('Odin', 'Bao', 'Brokkr', 'Veritas')
COMPLETED = {'done', 'completed', 'success', 'succeeded'}
FAILED = {'failed', 'error', 'cancelled', 'canceled', 'timed_out'}
IN_PROGRESS = {'running', 'in_progress', 'blocked', 'review', 'validating', 'ready', 'scheduled', 'pending', 'queued'}

def timestamp(value):
    """Return aware UTC datetime for Unix seconds or ISO-8601; otherwise None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().replace('.', '', 1).isdigit()):
            n = float(value)
            if not math.isfinite(n) or not (0 < n < 32503680000):
                return None
            return datetime.fromtimestamp(n, tz=timezone.utc)
        dt = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return None  # Unknown timezone: never guess.
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError, OSError):
        return None

def summarize_operations(tasks, runs, days=14, now=None, source_available=True):
    if days not in (7, 14, 30):
        raise ValueError('Unsupported operations window')
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = now.date()
    dates = [today - timedelta(days=days - 1 - n) for n in range(days)]
    timeline = {d.isoformat(): {'date': d.isoformat(), 'completed': 0, 'failed': 0} for d in dates}
    agents = {name: {'agent': name, 'tasks': 0, 'completed': 0, 'failed': 0, 'active_or_pending': 0,
                     'other': 0, 'completion_rate_pct': None} for name in AGENTS}
    no_terminal_stamp = 0
    ignored_assignees = 0
    for task in tasks:
        name = next((a for a in AGENTS if str(task.get('assignee') or '').casefold() == a.casefold()), None)
        if not name:
            ignored_assignees += 1
            continue
        a = agents[name]
        a['tasks'] += 1
        state = str(task.get('status') or '').lower().strip()
        kind = 'completed' if state in COMPLETED else 'failed' if state in FAILED else 'active_or_pending' if state in IN_PROGRESS else 'other'
        a[kind] += 1
        if kind in ('completed', 'failed'):
            dt = timestamp(task.get('completed_at'))
            if dt is None:
                no_terminal_stamp += 1
            else:
                date = dt.date().isoformat()
                if dt <= now and date in timeline:
                    timeline[date][kind] += 1
    for a in agents.values():
        resolved = a['completed'] + a['failed']
        a['completion_rate_pct'] = round(a['completed'] * 100 / resolved, 1) if resolved else None
    totals = {key: sum(a[key] for a in agents.values()) for key in ('tasks', 'completed', 'failed', 'active_or_pending', 'other')}
    resolved = totals['completed'] + totals['failed']
    totals['completion_rate_pct'] = round(totals['completed'] * 100 / resolved, 1) if resolved else None
    return {'read_only': True, 'source_status': 'available' if source_available else 'unavailable',
            'window_days': days, 'window_timezone': 'UTC', 'generated_at': now.isoformat(),
            'totals': totals, 'agents': list(agents.values()), 'timeline': list(timeline.values()),
            'coverage': {'unassigned_or_other_assignee_tasks': ignored_assignees,
                         'terminal_tasks_missing_completed_at': no_terminal_stamp,
                         'loaded_task_rows': len(tasks), 'loaded_run_rows': len(runs),
                         'task_query_cap': 5000},
            'definitions': {'completion_rate': 'completed / (completed + failed) tasks across loaded task history',
                            'timeline': 'Tasks with a terminal status and valid completed_at date, by UTC day',
                            'tasks': 'Task records, not unique executions; runs are not counted as tasks',
                            'note': 'Task history is capped at the latest 5000 rows; no completed_at means no timeline attribution.'}}
