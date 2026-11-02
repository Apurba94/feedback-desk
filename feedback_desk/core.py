"""Rules for a community feedback and complaints mechanism.

The hard rule: this app is not a safe place for details of abuse or danger, because its file is
not encrypted. A sensitive case records only a code and the referral made, and its text is
refused. Those details belong with a trained focal point, in a protected system.
"""
import re
from collections import Counter
from datetime import date, timedelta

CATEGORIES = {"information": ("Request for information", 3), "suggestion": ("Suggestion", 14), "complaint": ("Complaint about a service", 7), "thanks": ("Thanks", 14), "assistance": ("Request for assistance", 7), "sensitive": ("Sensitive case", 1)}
SENSITIVE_WORDS = """abuse abused assault rape sexual harass harassed harassment exploit exploitation bribe beaten threat threatened trafficking kidnap suicide
নির্যাতন ধর্ষণ যৌন হয়রানি ঘুষ হুমকি পাচার আত্মহত্যা মারধর""".split()
STATUSES = ("open", "in progress", "answered", "closed")
SMALL_CELL = 5


def looks_sensitive(text):
    """Words that suggest a case should go to a focal point. Returns those found. A person decides."""
    low = text.lower()
    return sorted({w for w in SENSITIVE_WORDS if (w in low if not w.isascii() else re.search(r"\b" + re.escape(w) + r"\b", low))})


def strip_contacts(text):
    """Remove phone numbers from text kept for reports."""
    return re.sub(r"\+?\d[\d\s-]{7,}\d", "[number removed]", text)


def due_date(category, opened):
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category}")
    return opened + timedelta(days=CATEGORIES[category][1])


def age_state(category, opened, answered, today):
    due = due_date(category, opened)
    if answered:
        return "answered on time" if answered <= due else "answered late"
    if today > due:
        return "overdue"
    return "due today" if today == due else "waiting"


def performance(cases, today):
    """cases: list of (category, opened, answered or None). The measures donors and communities ask about."""
    done = [c for c in cases if c[2]]
    late = [c for c in cases if age_state(c[0], c[1], c[2], today) == "overdue"]
    on_time = sum(1 for c in done if c[2] <= due_date(c[0], c[1]))
    days = [(c[2] - c[1]).days for c in done]
    return {"received": len(cases), "answered": len(done), "overdue": len(late), "answer_rate": len(done) / len(cases) if cases else None, "on_time_rate": on_time / len(done) if done else None, "mean_days": sum(days) / len(days) if days else None}


def by_week(dates):
    """Monday-start weeks, as {week start: count}, with empty weeks filled in."""
    if not dates:
        return {}
    start = {d - timedelta(days=d.weekday()) for d in dates}
    out = {}
    w = min(start)
    while w <= max(start):
        out[w] = 0
        w += timedelta(days=7)
    for d in dates:
        out[d - timedelta(days=d.weekday())] += 1
    return out


def rising_topics(recent, earlier, minimum=4):
    """Topics growing fast: compare recent counts with the earlier period."""
    a, b = Counter(recent), Counter(earlier)
    out = []
    for t, n in a.items():
        if n >= minimum and n >= 2 * max(b[t], 1):
            out.append((t, n, b[t]))
    return sorted(out, key=lambda r: -r[1])


def suppress(counts, limit=SMALL_CELL):
    """Hide small numbers in anything shared outside the team, so that a person cannot be worked out.
    If only one cell is hidden, its value can be found by subtraction, so hide the next smallest too."""
    out = {k: v for k, v in counts.items()}
    small = [k for k, v in counts.items() if 0 < v < limit]
    if len(small) == 1:
        others = sorted((v, k) for k, v in counts.items() if k not in small and v > 0)
        if others:
            small.append(others[0][1])
    for k in small:
        out[k] = f"fewer than {limit}" if counts[k] < limit else "hidden"
    return out
