from . import ui
from ..core import calculator
from ..core.planner import SPLITS, recommended_split
from ..core.profile import Profile, SEXES, LIFESTYLES, GOALS, EXPERIENCE, EQUIPMENT


def interview(name=None, old=None):
    """Ask all the questions. `old` (a Profile) supplies defaults when editing."""
    d = old.to_dict() if old else {}
    ui.header("Coach interview", "Answer a few questions so I can build your plan.")

    if name is None:
        while True:
            name = ui.ask("Your name", d.get("name"))
            if name:
                break
            ui.error("Name can't be empty.")

    ui.section("Your body")
    sex = ui.ask_choice("Sex (used in the calorie formula):",
                        [(s, s.title()) for s in SEXES], d.get("sex"))
    age = ui.ask_int("Age", 14, 90, d.get("age"))
    height = ui.ask_float("Height (cm)", 120, 230, d.get("height_cm"))
    weight = ui.ask_float("Current weight (kg)", 30, 300, d.get("weight_kg"))

    bmi_now = calculator.bmi(weight, height)
    low, high = calculator.healthy_weight_range(height)
    ui.info(f"  Your BMI is {bmi_now:.1f} ({calculator.bmi_category(bmi_now)}). "
            f"Healthy range for your height: {low:.0f}-{high:.0f} kg")

    target = ui.ask_float("Target weight (kg)", 30, 300, d.get("target_weight_kg", round(weight)))
    if calculator.bmi(target, height) < 18.5:
        ui.warn("That target is below a healthy BMI. I'll keep it, but please reconsider.")

    ui.section("Your goal & lifestyle")
    suggested = "lose" if target < weight - 0.5 else "gain" if target > weight + 0.5 else "maintain"
    goal = ui.ask_choice("Main goal:", list(GOALS.items()), d.get("goal", suggested))
    lifestyle = ui.ask_choice("Daily activity outside the gym:",
                              [(k, v[0]) for k, v in LIFESTYLES.items()], d.get("lifestyle"))

    ui.section("Your training")
    experience = ui.ask_choice("Training experience:", list(EXPERIENCE.items()), d.get("experience"))
    equipment = ui.ask_choice("Where do you train?", list(EQUIPMENT.items()), d.get("equipment"))
    days = ui.ask_int("How many days per week can you train? (1-6)", 1, 6, d.get("days_per_week", 3))
    hours = ui.ask_float("How many hours per session? (0.5 - 2.5)", 0.5, 2.5,
                         d.get("hours_per_session", 1))

    rec = recommended_split(days)
    options = [("auto", f"Let the coach decide → {SPLITS[rec][0]} (recommended)")]
    options += [(key, label) for key, (label, _) in SPLITS.items()]
    split = ui.ask_choice("Workout split:", options, d.get("split", "auto"))

    profile = Profile(name=name, sex=sex, age=age, height_cm=height, weight_kg=weight,
                      target_weight_kg=target, lifestyle=lifestyle, goal=goal,
                      experience=experience, equipment=equipment, days_per_week=days,
                      hours_per_session=hours, split=split)
    if "created" in d:
        profile.created = d["created"]
    return profile