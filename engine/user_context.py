import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ACTIVE_USER_PATH = BASE_DIR / "data" / "active_user.json"


def get_active_user() -> str:
    if not ACTIVE_USER_PATH.exists():
        return "boss"

    try:
        with open(ACTIVE_USER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("active_user", "boss")
    except Exception:
        return "boss"


def set_active_user(user: str):
    ACTIVE_USER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_USER_PATH, "w", encoding="utf-8") as f:
        json.dump({"active_user": user}, f, indent=2)