import shlex

from . import ui, views, session
from .onboarding import interview
from .. import __version__, storage
from ..core import planner
from ..export import export_plan

BANNER = r"""
   ______ _ _   ______
  |  ____(_) | |  ____|
  | |__   _| |_| |__ ___  _ __ __ _  ___
  |  __| | | __|  __/ _ \| '__/ _` |/ _ \
  | |    | | |_| | | (_) | | | (_| |  __/
  |_|    |_|\__|_|  \___/|_|  \__, |\___|
                               __/ |
     your personal trainer    |___/   v{v}
"""

# (command, usage, description) — also used to print the help screen.
HELP = [
    ("Your body", [
        ("stats", "stats", "BMI, calories for rest/training days, macros and water"),
        ("profile", "profile", "Show your profile"),
        ("edit", "edit", "Answer the coach interview again (rebuilds the plan)"),
        ("weight", "weight <kg>", "Log today's weight, e.g. weight 82.4"),
    ]),
    ("Your plan", [
        ("plan", "plan", "Weekly overview with time and calories per session"),
        ("today", "today", "Today's session"),
        ("day", "day <day|type>", "One day in detail, e.g. day monday / day push"),
        ("start", "start [day]", "Guided workout: the coach counts sets with you"),
        ("swap", "swap <old> with <new>", "Replace an exercise in your plan"),
        ("regen", "regen", "Generate a fresh plan from your profile"),
        ("export", "export", "Save your full plan to a Markdown file"),
    ]),
    ("Exercises", [
        ("exercise", "exercise <name>", "Info and coaching tip for an exercise"),
        ("search", "search <word>", "Search exercises by name or muscle"),
        ("library", "library [muscle]", "All exercises grouped by muscle"),
    ]),
    ("Progress", [
        ("progress", "progress", "Workouts, streak and weight chart"),
        ("forecast", "forecast", "When will you reach your target? + what-if table"),
        ("badges", "badges", "Your achievements"),
    ]),
    ("App", [
        ("switch", "switch", "Change user"),
        ("help", "help", "Show this list"),
        ("exit", "exit", "Save and quit"),
    ]),
]


def print_help():
    ui.header("Commands")
    for group, cmds in HELP:
        ui.section(group)
        for _, usage, desc in cmds:
            print(f"  {ui.color(f'{usage:<24}', 'green')}{desc}")


class Shell:
    def __init__(self):
        self.account = None
        self.running = True

    # ------------------------------------------------------------ login
    def login(self):
        users = storage.list_users()
        options = [(u, f"Continue as {u}") for u in users] + [("__new__", "Create a new trainee")]
        if users:
            choice = ui.ask_choice("Who's training today?", options)
        else:
            ui.info("Welcome! Let's set up your first profile.")
            choice = "__new__"

        if choice == "__new__":
            while True:
                name = ui.ask("Your name")
                if not name:
                    ui.error("Name can't be empty.")
                elif storage.exists(name):
                    ui.error("That name is taken. Pick another one.")
                else:
                    break
            profile = interview(name)
            self.account = storage.Account(profile)
            self.account.plan = planner.build_plan(profile)
            self.account.save()
            ui.success("Profile saved. Here's what I built for you:")
            views.show_stats(self.account)
            views.show_plan(self.account)
        else:
            self.account = storage.Account.load(choice)
            ui.success(f"Welcome back, {self.account.profile.name}!")
            self.greet()

    def greet(self):
        today = session.pick_today(self.account.plan)
        if today["session"]:
            print(f"  Today is {today['day']}: {ui.color(today['session']['type'], 'bold')} day. "
                  "Type `start` when you're ready.")
        else:
            nxt = session.next_training_day(self.account.plan)
            extra = f" Next session: {nxt['session']['type']} on {nxt['day']}." if nxt else ""
            print(f"  Today is a rest day.{extra}")

    # ------------------------------------------------------------- loop
    def run(self):
        print(ui.color(BANNER.format(v=__version__), "cyan", "bold"))
        try:
            self.login()
            ui.info("  Type `help` to see everything I can do.")
            while self.running:
                try:
                    line = input(ui.color(f"\n{self.account.profile.name} ▸ ", "bold", "magenta"))
                except EOFError:
                    break
                self.dispatch(line)
        except KeyboardInterrupt:
            print()
        if self.account:
            self.account.save()
        print(ui.color("\n  Saved. Stay strong! 💪\n", "green"))

    def dispatch(self, line):
        line = line.strip()
        if not line:
            return
        try:
            parts = shlex.split(line)
        except ValueError:
            parts = line.split()
        cmd, args = parts[0].lower(), parts[1:]
        handler = getattr(self, f"cmd_{cmd}", None)
        if handler is None:
            ui.error(f"Unknown command '{cmd}'. Type `help`.")
            return
        try:
            handler(" ".join(args))
        except KeyboardInterrupt:
            print()
            ui.warn("Cancelled.")

    # --------------------------------------------------------- commands
    def cmd_help(self, _):
        print_help()

    def cmd_stats(self, _):
        views.show_stats(self.account)

    def cmd_profile(self, _):
        views.show_profile(self.account)

    def cmd_edit(self, _):
        old = self.account.profile
        new = interview(old.name, old)
        self.account.profile = new
        if abs(new.weight_kg - old.weight_kg) > 0.01:
            self.account.log_weight(new.weight_kg)
        self.account.plan = planner.build_plan(new)
        self.account.save()
        ui.success("Profile updated and plan rebuilt.")
        views.show_plan(self.account)

    def cmd_weight(self, arg):
        try:
            kg = float(arg)
            if not 30 <= kg <= 300:
                raise ValueError
        except ValueError:
            ui.error("Usage: weight <kg>   e.g. weight 82.4")
            return
        previous = self.account.profile.weight_kg
        self.account.log_weight(kg)
        self.account.save()
        diff = kg - previous
        ui.success(f"Logged {kg:.1f} kg ({diff:+.1f} kg since last entry). Calories updated.")

    def cmd_plan(self, _):
        views.show_plan(self.account)

    def cmd_today(self, _):
        views.show_day(self.account, session.pick_today(self.account.plan))

    def cmd_day(self, arg):
        if not arg:
            ui.error("Usage: day <weekday or session type>, e.g. day monday")
            return
        d = planner.find_day(self.account.plan, arg)
        if d is None:
            ui.error(f"No day matches '{arg}'.")
            return
        views.show_day(self.account, d)

    def cmd_start(self, arg):
        plan = self.account.plan
        d = planner.find_day(plan, arg) if arg else session.pick_today(plan)
        if d is None:
            ui.error(f"No day matches '{arg}'.")
            return
        if not d["session"]:
            nxt = session.next_training_day(plan)
            ui.warn(f"{d['day']} is a rest day.")
            if not nxt or not ui.confirm(f"Do {nxt['day']}'s {nxt['session']['type']} session instead?"):
                return
            d = nxt
        session.run(self.account, d)

    def cmd_swap(self, arg):
        if " with " not in arg.lower():
            ui.error("Usage: swap <old exercise> with <new exercise>")
            return
        idx = arg.lower().index(" with ")
        old, new = arg[:idx], arg[idx + 6:]
        try:
            count = planner.swap_exercise(self.account.plan, old, new, self.account.profile)
        except ValueError as exc:
            ui.error(str(exc))
            return
        if count == 0:
            ui.error(f"'{old}' isn't in your plan. Check `plan` / `day <name>`.")
            return
        self.account.save()
        ui.success(f"Swapped in {count} session(s).")

    def cmd_regen(self, _):
        if ui.confirm("This replaces your current plan (and swaps). Continue?", default=False):
            self.account.plan = planner.build_plan(self.account.profile)
            self.account.save()
            views.show_plan(self.account)

    def cmd_export(self, _):
        path = export_plan(self.account)
        ui.success(f"Plan saved to {path}")

    def cmd_exercise(self, arg):
        if not arg:
            ui.error("Usage: exercise <name>")
            return
        views.show_exercise(arg)

    def cmd_search(self, arg):
        if not arg:
            ui.error("Usage: search <word>")
            return
        views.show_search(arg)

    def cmd_library(self, arg):
        views.show_library(arg.lower() or None)

    def cmd_progress(self, _):
        views.show_progress(self.account)

    def cmd_forecast(self, _):
        views.show_forecast(self.account)

    def cmd_badges(self, _):
        views.show_achievements(self.account)

    def cmd_switch(self, _):
        self.account.save()
        self.login()

    def cmd_exit(self, _):
        self.running = False

    cmd_quit = cmd_exit
