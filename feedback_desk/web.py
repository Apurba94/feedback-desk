"""The offline web app."""
from collections import Counter
from datetime import date, timedelta

from . import core
from .fieldkit import App, Fail, Raw, bar_chart, card, form, h, line_chart, link, redirect, stats, table

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, category TEXT NOT NULL, topic TEXT NOT NULL DEFAULT '', channel TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '', referred_to TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open', response TEXT NOT NULL DEFAULT '', opened TEXT NOT NULL, answered TEXT);
"""
CHANNELS = [(c, c) for c in ("Help desk", "Phone", "Community meeting", "Suggestion box", "Home visit")]


def create_app(db="feedback.db", today=date.today):
    a = App("Feedback Desk", db, SCHEMA, [("Overview", "/"), ("New case", "/new"), ("Report", "/report")])

    def rows_for_stats():
        return [(r["category"], date.fromisoformat(r["opened"]), date.fromisoformat(r["answered"]) if r["answered"] else None) for r in a.rows("SELECT * FROM cases")]

    def view(r):
        return "restricted" if r["category"] == "sensitive" else r["summary"]

    @a.route("/")
    def home(req):
        now = today()
        p = core.performance(rows_for_stats(), now)
        rows = a.rows("SELECT * FROM cases WHERE status NOT IN ('answered', 'closed') ORDER BY opened")
        rows = sorted(rows, key=lambda r: core.due_date(r["category"], date.fromisoformat(r["opened"])))

        def state(r):
            s = core.age_state(r["category"], date.fromisoformat(r["opened"]), None, now)
            return Raw(f'<span class="{"bad" if s == "overdue" else "warn" if s == "due today" else ""}">{s}</span>')
        body = stats([("Received", p["received"]), ("Answered", "n/a" if p["answer_rate"] is None else f"{p['answer_rate']:.0%}"), ("On time", "n/a" if p["on_time_rate"] is None else f"{p['on_time_rate']:.0%}"), ("Overdue", p["overdue"])])
        body += card("Waiting for a response", table(rows, [("Case", lambda r: link(f"/case/{r['id']}", r["code"])), ("Type", lambda r: core.CATEGORIES[r["category"]][0]), ("Summary", view), ("State", state)], "Nothing is waiting."))
        return a.page("Overview", body)

    @a.route("/new", ("GET", "POST"))
    def new(req):
        if req.method == "POST":
            category = req.text("category")
            if category not in core.CATEGORIES:
                raise Fail("Unknown type")
            summary = req.text("summary", False)
            hits = core.looks_sensitive(summary)
            if category == "sensitive":
                if summary:
                    raise Fail("Do not record details of a sensitive case here. Clear the summary, and pass the details to the focal point in person.")
                if not req.text("referred_to", False):
                    raise Fail("Say which focal point this was referred to.")
            elif hits and not req.get("confirmed"):
                raise Fail(f"This text may be sensitive ({', '.join(hits)}). If so, use the Sensitive case type and do not write details. If you have checked and it is not, tick the confirmation.")
            n = (a.one("SELECT COALESCE(MAX(id), 0) FROM cases") or 0) + 1
            code = f"FB-{today():%y%m}-{n:04d}"
            a.run("INSERT INTO cases (code, category, topic, channel, summary, area, referred_to, opened) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", code, category, req.text("topic", False), req.text("channel"), core.strip_contacts(summary), req.text("area", False), req.text("referred_to", False), today().isoformat())
            a.log("new case", code)
            return redirect("/")
        cats = [(k, v[0]) for k, v in core.CATEGORIES.items()]
        guide = '<p class="bad"><b>Sensitive cases:</b> abuse, exploitation or danger to someone. Record no details here. Refer at once to a trained focal point, and follow your safeguarding procedure.</p>'
        return a.page("New case", card("Record feedback", guide + form(a, "/new", [("category", "Type", "select", cats), ("channel", "How it came in", "select", CHANNELS), ("topic", "Topic, such as water or food"), ("area", "Area"), ("summary", "Summary, without names or phone numbers", "textarea"), ("referred_to", "Referred to"), ("confirmed", "I have checked this is not a sensitive case", "checkbox", "1")], "Save")))

    @a.route("/case/<id>", ("GET", "POST"))
    def case(req, id):
        r = a.row("SELECT * FROM cases WHERE id = ?", id)
        if r is None:
            raise Fail("No such case", 404)
        if req.method == "POST":
            status = req.text("status")
            if status not in core.STATUSES:
                raise Fail("Unknown status")
            response = req.text("response", False)
            if status == "answered" and r["category"] != "sensitive" and not response:
                raise Fail("Record what the person was told, so the loop is closed.")
            answered = today().isoformat() if status in ("answered", "closed") and not r["answered"] else r["answered"]
            a.run("UPDATE cases SET status = ?, response = ?, answered = ? WHERE id = ?", status, "" if r["category"] == "sensitive" else response, answered, id)
            a.log("update case", f"{r['code']} {status}")
            return redirect("/")
        return a.page(r["code"], stats([("Type", core.CATEGORIES[r["category"]][0]), ("Status", r["status"]), ("Due", core.due_date(r["category"], date.fromisoformat(r["opened"])).isoformat())]) + card("Summary", f"<p>{h(view(r))}</p>" + (f"<p>Referred to: {h(r['referred_to'])}</p>" if r["referred_to"] else "")) + card("Update", form(a, f"/case/{id}", [("status", "Status", "select", [(s, s) for s in core.STATUSES]), ("response", "What the person was told", "textarea", r["response"])], "Save")))

    @a.route("/report")
    def report(req):
        now = today()
        rows = a.rows("SELECT * FROM cases")
        dates = [date.fromisoformat(r["opened"]) for r in rows]
        weeks = core.by_week(dates)
        cut, old = now - timedelta(days=14), now - timedelta(days=28)
        recent = [r["topic"] for r in rows if r["topic"] and date.fromisoformat(r["opened"]) > cut]
        earlier = [r["topic"] for r in rows if r["topic"] and old < date.fromisoformat(r["opened"]) <= cut]
        rising = core.rising_topics(recent, earlier)
        counts = Counter(core.CATEGORIES[r["category"]][0] for r in rows)
        topics = Counter(r["topic"] for r in rows if r["topic"])
        safe = core.suppress(dict(counts))
        body = card("Shareable numbers (small counts hidden)", table([{"k": k, "v": v} for k, v in safe.items()], [("Type", "k"), ("Cases", "v")], "No cases yet."))
        body += card("Cases per week", line_chart([(k.isoformat(), v) for k, v in weeks.items()]))
        body += card("Topics", bar_chart(topics.most_common(10)))
        body += card("Rising topics", table(rising, [("Topic", lambda r: r[0]), ("Last two weeks", lambda r: r[1]), ("Two weeks before", lambda r: r[2])], "Nothing is rising fast."))
        return a.page("Report", body)

    return a
