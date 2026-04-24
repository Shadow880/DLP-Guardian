import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "logs" / "ai_policy_audit.log"


def log_decision(payload: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = dict(payload)
    entry["timestamp"] = datetime.now().isoformat()

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()