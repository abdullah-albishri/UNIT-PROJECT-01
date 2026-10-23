import os
import re
import sys

_ANSI = re.compile(r"\033\[[0-9;]*m")

# Enable ANSI escape codes on Windows terminals.
if os.name == "nt":
    os.system("")

_USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ

_CODES = {
    "bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33",
    "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
}


def color(text, *styles):
    """Wrap text in ANSI styles (no-op when colors are disabled)."""
    if not _USE_COLOR or not styles:
        return str(text)
    codes = ";".join(_CODES[s] for s in styles if s in _CODES)
    return f"\033[{codes}m{text}\033[0m"


def visible_len(text):
    """Length of a string ignoring ANSI escape codes."""
    return len(_ANSI.sub("", str(text)))


def pad(text, width):
    return str(text) + " " * max(0, width - visible_len(text))


def header(title, subtitle=""):
    line = "═" * 58
    print()
    print(color(line, "cyan"))
    print(color(f"  {title}", "bold", "cyan"))
    if subtitle:
        print(color(f"  {subtitle}", "dim"))
    print(color(line, "cyan"))


def section(title):
    print()
    print(color(f"▸ {title}", "bold", "yellow"))


def success(msg):
    print(color(f"✔ {msg}", "green"))


def warn(msg):
    print(color(f"! {msg}", "yellow"))


def error(msg):
    print(color(f"✘ {msg}", "red"))


def info(msg):
    print(color(msg, "dim"))


def table(headers, rows):
    """Print a simple aligned table."""
    cols = len(headers)
    widths = [visible_len(h) for h in headers]
    for row in rows:
        for i in range(cols):
            widths[i] = max(widths[i], visible_len(row[i]))
    sep = "  "
    print(sep.join(color(pad(h, widths[i]), "bold") for i, h in enumerate(headers)))
    print(sep.join("─" * w for w in widths))
    for row in rows:
        print(sep.join(pad(row[i], widths[i]) for i in range(cols)))


def bar(value, maximum, width=30, style="green"):
    """Return a horizontal progress bar string."""
    if maximum <= 0:
        filled = 0
    else:
        filled = int(round(width * min(value, maximum) / maximum))
    return color("█" * filled, style) + color("░" * (width - filled), "dim")


# ---------------------------------------------------------------- input ----

def ask(prompt, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    try:
        answer = input(color(f"{prompt}{suffix}: ", "cyan")).strip()
    except EOFError:
        # Input stream closed (Ctrl+D / Ctrl+Z): stop the app cleanly instead of looping.
        raise KeyboardInterrupt from None
    return answer if answer else ("" if default is None else str(default))


def ask_float(prompt, low, high, default=None):
    while True:
        raw = ask(prompt, default)
        try:
            value = float(raw)
        except ValueError:
            error("Please enter a number.")
            continue
        if low <= value <= high:
            return value
        error(f"Value must be between {low} and {high}.")


def ask_int(prompt, low, high, default=None):
    while True:
        raw = ask(prompt, default)
        if raw.isdigit() and low <= int(raw) <= high:
            return int(raw)
        error(f"Please enter a whole number between {low} and {high}.")


def ask_choice(prompt, options, default=None):
    """options: list of (key, label). Returns the chosen key."""
    print(color(prompt, "bold"))
    for i, (_, label) in enumerate(options, start=1):
        print(f"  {color(str(i), 'yellow')}) {label}")
    default_index = None
    if default is not None:
        for i, (key, _) in enumerate(options, start=1):
            if key == default:
                default_index = i
    index = ask_int("Choose", 1, len(options), default_index)
    return options[index - 1][0]


def confirm(prompt, default=True):
    hint = "Y/n" if default else "y/N"
    raw = ask(f"{prompt} ({hint})").lower()
    if not raw:
        return default
    return raw in ("y", "yes")