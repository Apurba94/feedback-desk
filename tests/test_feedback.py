import unittest
from datetime import date, timedelta

from feedback_desk import core, create_app
from feedback_desk.core import age_state, by_week, due_date, looks_sensitive, performance, rising_topics, strip_contacts, suppress

D = date(2026, 11, 2)


class TestRules(unittest.TestCase):
    def test_sensitive_words(self):
        self.assertEqual(looks_sensitive("He asked for a bribe"), ["bribe"])
        self.assertEqual(looks_sensitive("The tap is broken"), [])
        self.assertTrue(looks_sensitive("আমাকে হুমকি দিয়েছে"))
        self.assertEqual(looks_sensitive("the therapist helped"), [])

    def test_phone_numbers_are_removed(self):
        self.assertEqual(strip_contacts("call 01712 345 678 now"), "call [number removed] now")
        self.assertEqual(strip_contacts("needs 25 kg"), "needs 25 kg")

    def test_deadlines(self):
        self.assertEqual(due_date("sensitive", D), D + timedelta(days=1))
        self.assertEqual(due_date("complaint", D), D + timedelta(days=7))
        with self.assertRaises(ValueError):
            due_date("gossip", D)

    def test_states(self):
        self.assertEqual(age_state("information", D, None, D), "waiting")
        self.assertEqual(age_state("information", D, None, D + timedelta(days=3)), "due today")
        self.assertEqual(age_state("information", D, None, D + timedelta(days=4)), "overdue")
        self.assertEqual(age_state("information", D, D + timedelta(days=2), D), "answered on time")
        self.assertEqual(age_state("information", D, D + timedelta(days=9), D), "answered late")

    def test_performance(self):
        p = performance([("information", D, D + timedelta(days=1)), ("information", D, D + timedelta(days=9)), ("information", D, None)], D + timedelta(days=30))
        self.assertEqual((p["received"], p["answered"], p["overdue"], p["on_time_rate"], p["mean_days"]), (3, 2, 1, 0.5, 5))
        self.assertIsNone(performance([], D)["answer_rate"])

    def test_weeks_fill_gaps(self):
        w = by_week([date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 17)])
        self.assertEqual(list(w.values()), [2, 0, 1])

    def test_rising(self):
        self.assertEqual(rising_topics(["water"] * 6 + ["food"] * 5, ["food"] * 4), [("water", 6, 0)])


class TestSuppression(unittest.TestCase):
    def test_small_cells_are_hidden(self):
        out = suppress({"a": 50, "b": 3, "c": 2})
        self.assertEqual(out["a"], 50)
        self.assertEqual(out["b"], "fewer than 5")

    def test_a_lone_small_cell_cannot_be_recovered_by_subtraction(self):
        out = suppress({"a": 50, "b": 30, "c": 2})
        self.assertEqual(out["c"], "fewer than 5")
        self.assertEqual(out["b"], "hidden")
        self.assertEqual(out["a"], 50)

    def test_zero_is_not_hidden(self):
        self.assertEqual(suppress({"a": 0, "b": 9}), {"a": 0, "b": 9})


class TestApp(unittest.TestCase):
    def setUp(self):
        self.day = [D]
        self.a = create_app(":memory:", lambda: self.day[0])

    def add(self, **kw):
        base = dict(category="complaint", channel="Phone", topic="water", area="Block A", summary="Tap broken")
        return self.a.post("/new", **{**base, **kw})

    def text(self, url):
        return self.a.get(url).body.decode()

    def test_flow_closes_the_loop(self):
        self.assertEqual(self.add().status, 303)
        self.assertIn("Tap broken", self.text("/"))
        self.assertEqual(self.a.post("/case/1", status="answered").status, 400)
        self.assertEqual(self.a.post("/case/1", status="answered", response="Repaired on Tuesday").status, 303)
        self.assertNotIn("Tap broken", self.text("/"))
        self.assertIn("100%", self.text("/"))

    def test_sensitive_cases_cannot_hold_details(self):
        r = self.add(category="sensitive", summary="A named person did something", referred_to="Focal point")
        self.assertEqual(r.status, 400)
        self.assertEqual(self.a.one("SELECT COUNT(*) FROM cases"), 0)

    def test_sensitive_case_needs_a_referral_and_stays_restricted(self):
        self.assertEqual(self.add(category="sensitive", summary="").status, 400)
        self.assertEqual(self.add(category="sensitive", summary="", referred_to="PSEA focal point").status, 303)
        self.assertIn("restricted", self.text("/"))
        self.assertEqual(self.a.one("SELECT summary FROM cases"), "")
        self.a.post("/case/1", status="closed", response="details typed by mistake")
        self.assertEqual(self.a.one("SELECT response FROM cases"), "")

    def test_a_warning_word_stops_saving_until_checked(self):
        r = self.add(summary="Staff asked me for a bribe")
        self.assertEqual(r.status, 400)
        self.assertIn("may be sensitive", r.body.decode())
        self.assertEqual(self.add(summary="Staff asked me for a bribe", confirmed=1).status, 303)

    def test_phone_numbers_do_not_get_stored(self):
        self.add(summary="Call back on 01712345678")
        self.assertNotIn("01712345678", self.a.one("SELECT summary FROM cases"))

    def test_report_hides_small_counts(self):
        self.add()
        page = self.text("/report")
        self.assertIn("fewer than 5", page)

    def test_overdue_shows(self):
        self.add(category="information")
        self.day[0] = D + timedelta(days=5)
        self.assertIn("overdue", self.text("/"))

    def test_rising_topic_in_report(self):
        for _ in range(5):
            self.add()
        self.assertIn("water", self.text("/report").split("Rising topics")[1])

    def test_unknown_values(self):
        self.assertEqual(self.add(category="nope").status, 400)
        self.assertEqual(self.a.get("/case/9").status, 404)


if __name__ == "__main__":
    unittest.main()
