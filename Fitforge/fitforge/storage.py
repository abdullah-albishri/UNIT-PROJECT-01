import json
import os
import re
from datetime import date
from pathlib import Path
 
from .core.profile import Profile
 
SAVE_DIR = Path(os.environ.get("FITFORGE_SAVES", Path(__file__).resolve().parent.parent / "saves"))
 
 
def _slug(name):
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "user"
 
 
def path_for(name):
    return SAVE_DIR / f"{_slug(name)}.json"
 
 
def list_users():
    if not SAVE_DIR.exists():
        return []
    names = []
    for file in sorted(SAVE_DIR.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            names.append(data["profile"]["name"])
        except (ValueError, KeyError, OSError):
            continue
    return names
 
 
def exists(name):
    return path_for(name).exists()
 
 
class Account:
    """A loaded user: profile + plan + history."""
 
    def __init__(self, profile, plan=None, weights=None, workouts=None):
        self.profile = profile
        self.plan = plan
        self.weights = weights or [{"date": date.today().isoformat(), "kg": profile.weight_kg}]
        self.workouts = workouts or []
 
    def save(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        data = {"profile": self.profile.to_dict(), "plan": self.plan,
                "weights": self.weights, "workouts": self.workouts}
        tmp = path_for(self.profile.name).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path_for(self.profile.name))
 
    @classmethod
    def load(cls, name):
        data = json.loads(path_for(name).read_text(encoding="utf-8"))
        return cls(Profile.from_dict(data["profile"]), data.get("plan"),
                   data.get("weights"), data.get("workouts"))
 
    def log_weight(self, kg, when=None):
        when = when or date.today().isoformat()
        self.weights = [w for w in self.weights if w["date"] != when]
        self.weights.append({"date": when, "kg": kg})
        self.weights.sort(key=lambda w: w["date"])
        self.profile.weight_kg = self.weights[-1]["kg"]
 
 
def delete(name):
    p = path_for(name)
    if p.exists():
        p.unlink()