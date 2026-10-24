import unittest
from dataclasses import replace

from fitforge.core import calculator, planner
from fitforge.core.profile import Profile
from fitforge.data import exercises as db


def make_profile(**changes):
    base = Profile(name="Test", sex="male", age=25, height_cm=180, weight_kg=90,
                   target_weight_kg=80, lifestyle="sedentary", goal="lose",
                   experience="intermediate", equipment="gym",
                   days_per_week=4, hours_per_session=1.0)
    return replace(base, **changes)


class CalculatorTests(unittest.TestCase):
    def test_bmi(self):
        self.assertAlmostEqual(calculator.bmi(90, 180), 27.78, places=2)
        self.assertEqual(calculator.bmi_category(27.78), "Overweight")

    def test_bmr_mifflin(self):
        # 10*90 + 6.25*180 - 5*25 + 5 = 1905
        self.assertAlmostEqual(calculator.bmr("male", 90, 180, 25), 1905)
        self.assertAlmostEqual(calculator.bmr("female", 90, 180, 25), 1739)

    def test_kcal_per_minute(self):
        # MET 6, 90 kg -> 6*3.5*90/200 = 9.45
        self.assertAlmostEqual(calculator.kcal_per_minute(6, 90), 9.45)

    def test_calorie_floor(self):
        p = make_profile(sex="female", weight_kg=45, height_cm=150, age=60, target_weight_kg=40)
        self.assertGreaterEqual(calculator.target_calories(p), 1200)

    def test_lose_goal_reaches_target(self):
        p = make_profile()
        weeks = calculator.weeks_to_target(p, weekly_workout_burn=2000)
        self.assertIsNotNone(weeks)
        self.assertGreater(weeks, 0)

    def test_training_makes_fat_loss_faster(self):
        p = make_profile()
        self.assertLess(calculator.weeks_to_target(p, 3000), calculator.weeks_to_target(p, 0))

    def test_wrong_direction_returns_none(self):
        p = make_profile(goal="gain")  # target is lower than current weight
        self.assertIsNone(calculator.weeks_to_target(p, 2000))


class PlannerTests(unittest.TestCase):
    def test_recommended_split(self):
        self.assertEqual(planner.recommended_split(3), "full_body")
        self.assertEqual(planner.recommended_split(4), "upper_lower")
        self.assertEqual(planner.recommended_split(6), "ppl")

    def test_plan_has_right_number_of_sessions(self):
        for days in range(1, 7):
            plan = planner.build_plan(make_profile(days_per_week=days))
            sessions = [d for d in plan["week"] if d["session"]]
            self.assertEqual(len(sessions), days)
            self.assertEqual(len(plan["week"]), 7)

    def test_session_fits_time(self):
        for hours in (0.5, 1.0, 1.5, 2.0):
            p = make_profile(hours_per_session=hours)
            for d in planner.build_plan(p)["week"]:
                if d["session"]:
                    # at least 3 exercises are always kept, so allow a small overflow on short sessions
                    limit = p.session_minutes + (15 if hours < 1 else 0)
                    self.assertLessEqual(planner.session_minutes(d["session"]), limit)

    def test_no_duplicate_exercises_in_a_session(self):
        plan = planner.build_plan(make_profile(days_per_week=6, hours_per_session=2))
        for d in plan["week"]:
            if d["session"]:
                names = [i["name"] for i in d["session"]["exercises"]]
                self.assertEqual(len(names), len(set(names)))

    def test_home_plan_uses_home_equipment_only(self):
        plan = planner.build_plan(make_profile(equipment="home", days_per_week=5))
        for d in plan["week"]:
            if d["session"]:
                for item in d["session"]["exercises"]:
                    self.assertIn("home", db.find(item["name"])["equipment"])

    def test_swap(self):
        p = make_profile(days_per_week=6, split="ppl")
        plan = planner.build_plan(p)
        first = next(d for d in plan["week"] if d["session"])["session"]["exercises"][0]["name"]
        count = planner.swap_exercise(plan, first, "Push-Up", p)
        self.assertGreaterEqual(count, 1)
        with self.assertRaises(ValueError):
            planner.swap_exercise(plan, "Push-Up", "Flying Kick", p)

    def test_calories_positive(self):
        p = make_profile()
        plan = planner.build_plan(p)
        self.assertGreater(planner.weekly_burn(plan, p.weight_kg), 0)


if __name__ == "__main__":
    unittest.main()