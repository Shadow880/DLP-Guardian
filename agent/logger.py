import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("logs/ai_policy_audit.log")


def log_decision(payload: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        **payload
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")