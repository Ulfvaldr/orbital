"""Read-only Hermes usage summaries for Orbital."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

AGENTS = ("odin", "bao", "brokkr", "veritas")
PERIODS = ("today", "7d", "30d", "all")
METRICS = ("usage_records", "api_calls", "input_tokens", "output_tokens",
           "cache_read_tokens", "cache_write_tokens", "reasoning_tokens",
           "estimated_cost_usd", "estimated_records", "included_records",
           "unclassified_records")


def usage_root():
    return Path.home() / "AppData" / "Local" / "hermes" / "profiles"


def _timestamp(value):
    """Normalize SQLite epoch or ISO timestamps to timezone-aware UTC."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().replace('.', '', 1).isdigit()):
            n = float(value)
            if abs(n) >= 1e11:  # epoch milliseconds
                n /= 1000
            return datetime.fromtimestamp(n, timezone.utc)
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError, TypeError):
        return None


def _cutoff(period, now):
    if period == "all":
        return None
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    return (now - timedelta(days=7 if period == "7d" else 30)).astimezone(timezone.utc)


def summarize_agent(name, root=None, period="all", now=None):
    if name not in AGENTS:
        raise ValueError("Unsupported agent")
    if period not in PERIODS:
        raise ValueError("Unsupported period")

    local_now = now or datetime.now().astimezone()
    if local_now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    cutoff = _cutoff(period, local_now)
    base = Path(root) if root is not None else usage_root()
    path = base / name / "state.db"
    result = {"agent": name, "source_status": "unavailable",
              **{field: None for field in METRICS},
              "excluded_undated_records": None}
    if not path.is_file():
        return result

    try:
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        try:
            # Records are small (~hundreds per profile); Python parses heterogeneous
            # Hermes ISO/epoch timestamp formats without DB-side date coercion.
            columns = [r[1] for r in db.execute("PRAGMA table_info(session_model_usage)")]
            if period != "all" and "last_seen" not in columns and "first_seen" not in columns:
                return result  # Cannot claim a time-filtered total without timestamps.
            date_cols = [col for col in ("last_seen", "first_seen") if col in columns]
            chosen = "api_call_count, input_tokens, output_tokens, cache_read_tokens, " \
                     "cache_write_tokens, reasoning_tokens, estimated_cost_usd, cost_status"
            rows = db.execute("SELECT " + chosen +
                              (", " + ", ".join(date_cols) if date_cols else "") +
                              " FROM session_model_usage").fetchall()
        finally:
            db.close()

        result.update({field: 0 for field in METRICS})
        result["excluded_undated_records"] = 0
        for row in rows:
            calls, inputs, outputs, cache_read, cache_write, reasoning, cost, status = row[:8]
            if cutoff is not None:
                stamp = next((stamp for stamp in (_timestamp(v) for v in row[8:]) if stamp is not None), None)
                if stamp is None:
                    result["excluded_undated_records"] += 1
                    continue
                if stamp < cutoff or stamp > local_now.astimezone(timezone.utc):
                    continue
            result["usage_records"] += 1
            for field, value in zip(METRICS[1:7], (calls, inputs, outputs, cache_read, cache_write, reasoning)):
                result[field] += value or 0
            if status == "estimated":
                result["estimated_records"] += 1
                result["estimated_cost_usd"] += cost or 0
            elif status == "included":
                result["included_records"] += 1
            else:
                result["unclassified_records"] += 1
        result["source_status"] = "available"
    except (sqlite3.Error, OSError, ValueError, TypeError):
        pass
    return result



def summarize_models(name, root=None, period="all", now=None):
    """Read-only per-model/provider totals using the same activity window."""
    if name not in AGENTS:
        raise ValueError("Unsupported agent")
    if period not in PERIODS:
        raise ValueError("Unsupported period")
    local_now = now or datetime.now().astimezone()
    if local_now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    cutoff = _cutoff(period, local_now)
    path = (Path(root) if root is not None else usage_root()) / name / "state.db"
    if not path.is_file():
        return []
    try:
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        try:
            cols = {row[1] for row in db.execute("PRAGMA table_info(session_model_usage)")}
            if period != "all" and not ({"last_seen", "first_seen"} & cols):
                return []
            optional = ("model", "billing_provider", "billing_mode", "last_seen", "first_seen")
            mandatory = ("api_call_count", "input_tokens", "output_tokens", "cache_read_tokens",
                         "cache_write_tokens", "reasoning_tokens", "estimated_cost_usd", "cost_status")
            # NULL placeholders allow old Hermes schemas to remain viewable.
            names = mandatory + optional
            selected = ", ".join(('"' + key + '"') if key in cols else ('NULL AS "' + key + '"') for key in names)
            rows = db.execute("SELECT " + selected + " FROM session_model_usage").fetchall()
        finally:
            db.close()
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return []

    groups = {}
    upper = local_now.astimezone(timezone.utc)
    for row in rows:
        calls, inputs, outputs, cache_read, cache_write, reasoning, cost, status, model, provider, mode, last, first = row
        if cutoff is not None:
            stamp = _timestamp(last) or _timestamp(first)
            if stamp is None or stamp < cutoff or stamp > upper:
                continue
        key = (str(model or "Unknown model"), str(provider or "Unknown provider"), str(mode or "Unknown mode"))
        if key not in groups:
            groups[key] = {"agent": name, "model": key[0], "provider": key[1], "billing_mode": key[2],
                           **{field: 0 for field in METRICS}}
        result = groups[key]
        result["usage_records"] += 1
        for field, value in zip(METRICS[1:7], (calls, inputs, outputs, cache_read, cache_write, reasoning)):
            result[field] += value or 0
        if status == "estimated":
            result["estimated_records"] += 1
            result["estimated_cost_usd"] += cost or 0
        elif status == "included":
            result["included_records"] += 1
        else:
            result["unclassified_records"] += 1
    return sorted(groups.values(), key=lambda row: (row["agent"], -row["input_tokens"], row["model"], row["provider"]))

def usage_payload(period="all", now=None):
    if period not in PERIODS:
        raise ValueError("Unsupported period")
    agents = [summarize_agent(name, period=period, now=now) for name in AGENTS]
    return {
        "agents": agents,
        "models": [item for name in AGENTS for item in summarize_models(name, period=period, now=now)],
        "period": period,
        "read_only": True,
        "cost_note": (
            "Estimated costs are not verified provider charges. "
            "Subscription-included and unclassified records are reported separately. "
            "Filtered periods use last_seen (falling back to first_seen); "
            "untimestamped records are excluded. Today uses the server's local timezone."
        ),
    }
