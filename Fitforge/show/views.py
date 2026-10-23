from dataclasses import replace
from datetime import date, timedelta

from . import ui
from ..core import calculator, planner, progress
from ..core.profile import GOALS, LIFESTYLES, EXPERIENCE, EQUIPMENT
from ..data import exercises as db


def _avg_session_burn(account):
    sessions = [d["session"] for d in account.plan["week"] if d["session"]]
    if not sessions:
        return 0.0
    w = account.profile.weight_kg
    return sum(planner.session_calories(s, w)["total"] for s in sessions) / len(sessions)


# ---------------------------------------------------------------- profile

def show_profile(account):
    p = account.profile
    ui.header(f"{p.name}'s profile", f"Member since {p.created}")
    rows = [
        ["Sex / Age", f"{p.sex.title()}, {p.age}"],
        ["Height", f"{p.height_cm:.0f} cm"],
        ["Weight → Target", f"{p.weight_kg:.1f} kg → {p.target_weight_kg:.1f} kg"],
        ["Goal", GOALS[p.goal]],
        ["Lifestyle", LIFESTYLES[p.lifestyle][0]],
        ["Experience", EXPERIENCE[p.experience]],
        ["Equipment", EQUIPMENT[p.equipment]],
        ["Schedule", f"{p.days_per_week} days/week × {p.hours_per_session:g} h"],
        ["Split", account.plan["split_name"]],
    ]
    ui.table(["Field", "Value"], rows)


# ------------------------------------------------------------------ stats

def show_stats(account):
    p = account.profile
    ui.header("Body & nutrition report", "Based on the Mifflin-St Jeor equation")

    value = calculator.bmi(p.weight_kg, p.height_cm)
    low, high = calculator.healthy_weight_range(p.height_cm)
    ui.section("Body")
    print(f"  BMI ............ {ui.color(f'{value:.1f}', 'bold')} ({calculator.bmi_category(value)})")
    print(f"  Healthy weight . {low:.0f} - {high:.0f} kg for {p.height_cm:.0f} cm")
    print(f"  BMR ............ {calculator.bmr(p.sex, p.weight_kg, p.height_cm, p.age):.0f} kcal "
          "(what your body burns at complete rest)")

    burn = _avg_session_burn(account)
    rest_cal = calculator.target_calories(p, 0)
    train_cal = calculator.target_calories(p, burn)

    ui.section("Daily calories")
    ui.table(["", "Rest day", "Training day"], [
        ["Maintenance", f"{calculator.maintenance_calories(p):.0f}",
         f"{calculator.maintenance_calories(p) + burn:.0f}"],
        ["Workout burn", "0", f"~{burn:.0f}"],
        [ui.color("Eat this", "bold", "green"), ui.color(f"{rest_cal:.0f} kcal", "bold", "green"),
         ui.color(f"{train_cal:.0f} kcal", "bold", "green")],
    ])
    adj = calculator.GOAL_ADJUSTMENT[p.goal]
    if adj:
        word = "deficit" if adj < 0 else "surplus"
        ui.info(f"  Includes a {abs(adj)} kcal {word} for your goal ({GOALS[p.goal]}).")
    if p.goal == "lose":
        ui.info("  On training days you eat back only half of the workout burn, "
                "so training speeds up fat loss.")

    ui.section("Macros on a training day")
    m = calculator.macros(p, train_cal)
    total = m["protein"] * 4 + m["fat"] * 9 + m["carbs"] * 4
    for key, per_g, style in (("protein", 4, "red"), ("carbs", 4, "yellow"), ("fat", 9, "blue")):
        kcal = m[key] * per_g
        print(f"  {key.title():<8} {m[key]:>5.0f} g  {ui.bar(kcal, total, 25, style)} {kcal / total:>4.0%}")

    ui.section("Water")
    print(f"  Rest day ~{calculator.water_liters(p.weight_kg):.1f} L   ·   "
          f"Training day ~{calculator.water_liters(p.weight_kg, p.session_minutes):.1f} L")


# ------------------------------------------------------------------- plan

def show_plan(account):
    p, plan = account.profile, account.plan
    ui.header(f"Weekly plan · {plan['split_name']}",
              f"{p.days_per_week} sessions × {p.hours_per_session:g} h · goal: {GOALS[p.goal]}")
    today = (date.today().weekday() + 1) % 7  # 0 = Sunday
    rows = []
    for i, d in enumerate(plan["week"]):
        name = d["day"] + (ui.color("  ← today", "magenta") if i == today else "")
        s = d["session"]
        if s:
            kcal = planner.session_calories(s, p.weight_kg)["total"]
            rows.append([name, ui.color(s["type"], "bold"), f"{len(s['exercises'])} exercises",
                         f"{planner.session_minutes(s):.0f} min", f"~{kcal:.0f} kcal"])
        else:
            rows.append([name, ui.color("Rest & recover", "dim"), "", "", ""])
    ui.table(["Day", "Session", "Work", "Time", "Burn"], rows)
    week_burn = planner.weekly_burn(plan, p.weight_kg)
    print()
    print(f"  Weekly workout burn: {ui.color(f'~{week_burn:.0f} kcal', 'bold', 'green')}"
          f"  (≈ {week_burn / calculator.KCAL_PER_KG_FAT:.2f} kg of fat)")
    longest = max((planner.session_minutes(d["session"]) for d in plan["week"] if d["session"]), default=0)
    if p.session_minutes - longest > 10:
        ui.warn(f"  Coach note: your sessions need ~{longest:.0f} min. More lifting than that "
                "won't help — spend the extra time walking or stretching.")
    ui.info("  Type `day <name>` (e.g. day sunday, day push) to see the exercises.")


def show_day(account, day):
    p = account.profile
    s = day["session"]
    if not s:
        ui.header(f"{day['day']} · Rest day")
        print("  Recovery is when muscles grow. Go for a light walk, stretch, sleep 7-9 h.")
        return
    cal = planner.session_calories(s, p.weight_kg)
    ui.header(f"{day['day']} · {s['type']}",
              f"~{planner.session_minutes(s):.0f} min · ~{cal['total']:.0f} kcal")
    print(f"  🔸 Warm-up: {s['warmup']} min light cardio + mobility (~{cal['warmup']:.0f} kcal)")
    print()
    rows = []
    for n, item in enumerate(s["exercises"], start=1):
        kcal = calculator.kcal_per_minute(item["met"], p.weight_kg) * item["minutes"]
        rows.append([str(n), item["name"], item["muscle"], f"{item['sets']} × {item['reps']}",
                     f"{item['rest']} s", f"{item['minutes']:.0f} min", f"{kcal:.0f}"])
    ui.table(["#", "Exercise", "Muscle", "Sets × Reps", "Rest", "Time", "kcal"], rows)
    print()
    if s["cardio"]:
        c = s["cardio"]
        print(f"  🔸 Cardio finisher: {c['name']} · {c['minutes']} min (~{cal['cardio']:.0f} kcal)")
    print(f"  🔸 Cool-down: {s['cooldown']} min stretching (~{cal['cooldown']:.0f} kcal)")
    ui.info("\n  Type `start` to do this workout with the coach, or `swap <old> with <new>`.")


# ----------------------------------------------------------- exercise lib

def show_exercise(name):
    ex = db.find(name)
    if not ex:
        matches = db.search(name)
        if len(matches) == 1:
            ex = matches[0]
        else:
            ui.error(f"No exercise called '{name}'. Try `search {name}`.")
            return
    ui.header(ex["name"], f"{ex['muscle'].title()} · {'Compound' if ex['compound'] else 'Isolation'}")
    print(f"  Where   : {', '.join(ex['equipment'])}")
    print(f"  MET     : {ex['met']}  (intensity used for calorie estimates)")
    print(f"  Coach   : {ui.color(ex['tip'], 'green')}")


def show_search(keyword):
    results = db.search(keyword)
    if not results:
        ui.error(f"Nothing found for '{keyword}'.")
        return
    ui.table(["Exercise", "Muscle", "Type", "Where"],
             [[e["name"], e["muscle"], "compound" if e["compound"] else "isolation",
               "/".join(e["equipment"])] for e in results])


def show_library(muscle=None):
    muscles = sorted({e["muscle"] for e in db.EXERCISES})
    if muscle and muscle not in muscles:
        ui.error(f"Unknown muscle. Choose from: {', '.join(muscles)}")
        return
    for m in ([muscle] if muscle else muscles):
        names = [e["name"] for e in db.EXERCISES if e["muscle"] == m]
        print(f"  {ui.color(m.title(), 'bold', 'yellow'):<22} {', '.join(names)}")
