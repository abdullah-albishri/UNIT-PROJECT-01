import sys
import time
from datetime import date

from . import ui
from ..core import calculator, progress
from ..data import exercises as db


def _target_reps(reps_text):
    """'12-15' -> 12"""
    return int(reps_text.split("-")[0])


def rest_timer(seconds):
    """Countdown that can be skipped with Ctrl+C."""
    try:
        for left in range(seconds, 0, -1):
            sys.stdout.write(f"\r  ⏱  Rest {left:>3}s  (Ctrl+C to skip) ")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\r  ⏱  Rest done! Next set.           \n")
    except KeyboardInterrupt:
        sys.stdout.write("\r  ⏱  Rest skipped.                    \n")


def run(account, day):
    """Run a session interactively. Returns the logged workout dict or None."""
    p = account.profile
    s = day["session"]
    ui.header(f"Let's go, {p.name}! · {s['type']}",
              "Enter = target reps · s = skip exercise · q = finish early")
    use_timer = ui.confirm("Use the rest timer between sets?", default=False)
    started = time.monotonic()

    print(f"\n  🔸 Warm-up: {s['warmup']} min of light cardio + arm circles, leg swings.")
    ui.ask("Press Enter when you're warmed up")

    done_sets = total_sets = 0
    volume = 0.0
    active_minutes = 0.0
    lifting_kcal = 0.0
    quit_early = False

    for n, item in enumerate(s["exercises"], start=1):
        total_sets += item["sets"]
        if quit_early:
            continue
        ex = db.find(item["name"])
        print()
        print(ui.color(f"  [{n}/{len(s['exercises'])}] {item['name']}", "bold", "yellow")
              + f"  ·  {item['sets']} × {item['reps']}  ·  rest {item['rest']} s")
        if ex:
            ui.info(f"  Tip: {ex['tip']}")
        load_raw = ui.ask("  Weight used in kg (Enter = bodyweight)", "")
        try:
            load = float(load_raw) if load_raw else 0.0
        except ValueError:
            load = 0.0

        completed = 0
        for set_no in range(1, item["sets"] + 1):
            target = _target_reps(item["reps"])
            raw = ui.ask(f"    Set {set_no}/{item['sets']} — reps done", target).lower()
            if raw == "q":
                quit_early = True
                break
            if raw == "s":
                ui.info("    Skipped.")
                break
            reps = int(raw) if raw.isdigit() and int(raw) <= 100 else target
            completed += 1
            volume += reps * load
            if reps >= target + 3:
                ui.success("    Strong! Consider adding weight next time.")
            if use_timer and set_no < item["sets"]:
                rest_timer(item["rest"])
        done_sets += completed
        fraction = completed / item["sets"]
        active_minutes += item["minutes"] * fraction
        lifting_kcal += calculator.kcal_per_minute(item["met"], p.weight_kg) * item["minutes"] * fraction

    cardio_kcal = cardio_min = 0.0
    if s["cardio"] and not quit_early:
        c = s["cardio"]
        print()
        print(ui.color(f"  Cardio finisher: {c['name']} for {c['minutes']} min", "bold", "yellow"))
        cardio_min = ui.ask_float("  Minutes you did (0 to skip)", 0, 120, c["minutes"])
        cardio_kcal = calculator.kcal_per_minute(c["met"], p.weight_kg) * cardio_min

    if done_sets == 0 and cardio_min == 0:
        ui.warn("No sets done — nothing logged. See you next time!")
        return None

    warm_cool = (calculator.kcal_per_minute(db.WARMUP_MET, p.weight_kg) * s["warmup"]
                 + calculator.kcal_per_minute(db.COOLDOWN_MET, p.weight_kg) * s["cooldown"])
    kcal = lifting_kcal + cardio_kcal + warm_cool
    minutes = s["warmup"] + active_minutes + cardio_min + s["cooldown"]
    real_minutes = (time.monotonic() - started) / 60

    before = progress.unlocked(account)
    workout = {"date": date.today().isoformat(), "type": s["type"], "minutes": round(minutes, 1),
               "kcal": round(kcal), "sets": done_sets, "volume": round(volume, 1)}
    account.workouts.append(workout)
    account.save()

    ui.header("Workout complete 💪")
    print(f"  Sets      {ui.bar(done_sets, total_sets, 25)} {done_sets}/{total_sets}")
    print(f"  Volume    {volume:,.0f} kg")
    print(f"  Time      ~{minutes:.0f} min planned-equivalent ({real_minutes:.0f} min on the clock)")
    print(f"  Burned    {ui.color(f'~{kcal:.0f} kcal', 'bold', 'green')}")
    eat = calculator.target_calories(p, kcal)
    print(f"  Eat today ~{eat:.0f} kcal, with {calculator.macros(p, eat)['protein']:.0f} g protein")
    print(f"\n  🔸 Don't forget your {s['cooldown']}-minute cool-down stretch.")

    new = progress.unlocked(account) - before
    for key, title, desc in progress.ACHIEVEMENTS:
        if key in new:
            print(ui.color(f"\n  🏆 Achievement unlocked: {title} — {desc}", "bold", "magenta"))
    return workout


def pick_today(plan):
    index = (date.today().weekday() + 1) % 7  # Python: Monday=0 → our Sunday=0
    return plan["week"][index]


def next_training_day(plan):
    index = (date.today().weekday() + 1) % 7
    for offset in range(1, 8):
        d = plan["week"][(index + offset) % 7]
        if d["session"]:
            return d
    return None
