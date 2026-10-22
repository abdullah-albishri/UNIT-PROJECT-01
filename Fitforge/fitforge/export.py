from datetime import date
from pathlib import Path
 
from .core import calculator, planner
from .core.profile import GOALS
 
EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"
 
 
def plan_to_markdown(account):
    p, plan = account.profile, account.plan
    sessions = [d["session"] for d in plan["week"] if d["session"]]
    burns = [planner.session_calories(s, p.weight_kg)["total"] for s in sessions]
    avg_burn = sum(burns) / len(burns) if burns else 0
    train_cal = calculator.target_calories(p, avg_burn)
    m = calculator.macros(p, train_cal)
 
    lines = [
        f"# FitForge plan for {p.name}",
        f"_Generated {date.today().isoformat()}_",
        "",
        "## Summary",
        f"- Goal: **{GOALS[p.goal]}** ({p.weight_kg:.1f} kg → {p.target_weight_kg:.1f} kg)",
        f"- BMI: {calculator.bmi(p.weight_kg, p.height_cm):.1f}",
        f"- Split: {plan['split_name']}, {p.days_per_week} days × {p.hours_per_session:g} h",
        f"- Calories: rest day **{calculator.target_calories(p):.0f} kcal**, "
        f"training day **{train_cal:.0f} kcal**",
        f"- Macros (training day): protein {m['protein']:.0f} g · carbs {m['carbs']:.0f} g · "
        f"fat {m['fat']:.0f} g",
        f"- Weekly workout burn: ~{sum(burns):.0f} kcal",
        "",
        "## Weekly program",
    ]
    for d in plan["week"]:
        s = d["session"]
        if not s:
            lines += ["", f"### {d['day']} — Rest"]
            continue
        cal = planner.session_calories(s, p.weight_kg)
        lines += ["", f"### {d['day']} — {s['type']} "
                      f"(~{planner.session_minutes(s):.0f} min, ~{cal['total']:.0f} kcal)",
                  "", f"Warm-up {s['warmup']} min", "",
                  "| # | Exercise | Sets × Reps | Rest |", "|---|---|---|---|"]
        for n, item in enumerate(s["exercises"], start=1):
            lines.append(f"| {n} | {item['name']} | {item['sets']} × {item['reps']} | {item['rest']} s |")
        if s["cardio"]:
            lines += ["", f"Cardio: {s['cardio']['name']} — {s['cardio']['minutes']} min"]
        lines += ["", f"Cool-down {s['cooldown']} min"]
    return "\n".join(lines) + "\n"
 
 
def export_plan(account):
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in account.profile.name.lower())
    path = EXPORT_DIR / f"{safe}_plan_{date.today().isoformat()}.md"
    path.write_text(plan_to_markdown(account), encoding="utf-8")
    return path
 