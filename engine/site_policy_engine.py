import json
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_POLICIES_PATH = BASE_DIR / "data" / "site_policies.json"

VALID_MODES = ["monitor", "warn", "strict"]


def load_site_policies():
    if not SITE_POLICIES_PATH.exists():
        return []

    try:
        with open(SITE_POLICIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_site_policies(policies: list):
    SITE_POLICIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_POLICIES_PATH, "w", encoding="utf-8") as f:
        json.dump(policies, f, indent=2)


def normalize_domain(source: str) -> str:
    if not source:
        return ""

    source = source.strip()

    if source.startswith("http://") or source.startswith("https://"):
        try:
            return urlparse(source).netloc.lower()
        except Exception:
            return source.lower()

    return source.lower()


def get_site_policy(source: str):
    domain = normalize_domain(source)
    policies = load_site_policies()

    for policy in policies:
        policy_domain = str(policy.get("domain", "")).lower()
        if not policy.get("enabled", True):
            continue

        if domain == policy_domain or domain.endswith("." + policy_domain):
            return policy

    return {
        "domain": domain,
        "label": domain or "unknown",
        "mode": "strict",
        "enabled": True
    }


def upsert_site_policy(domain: str, label: str, mode: str, enabled: bool):
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode: {mode}")

    domain = normalize_domain(domain)
    policies = load_site_policies()

    updated = False
    for policy in policies:
        if str(policy.get("domain", "")).lower() == domain:
            policy["label"] = label
            policy["mode"] = mode
            policy["enabled"] = enabled
            updated = True
            break

    if not updated:
        policies.append({
            "domain": domain,
            "label": label,
            "mode": mode,
            "enabled": enabled
        })

    save_site_policies(policies)


def delete_site_policy(domain: str):
    domain = normalize_domain(domain)
    policies = load_site_policies()
    policies = [p for p in policies if str(p.get("domain", "")).lower() != domain]
    save_site_policies(policies)


def adjust_decision_by_site(source: str, decision: dict) -> dict:
    site_policy = get_site_policy(source)
    mode = site_policy.get("mode", "strict")

    decision["site_policy"] = site_policy

    if mode == "strict":
        decision["site_adjustment"] = "none"
        return decision

    if mode == "warn":
        if decision.get("action") == "block":
            pattern_hits = decision.get("pattern_hits", []) or []
            hard_types = {"api_key", "bearer_token", "password", "env_secret", "private_key", "pan", "aadhaar"}
            pattern_types = {hit.get("type", "") for hit in pattern_hits}

            if pattern_types & hard_types:
                decision["site_adjustment"] = "none_hard_block"
                return decision

            decision["action"] = "warn"
            decision["allowed"] = False
            decision["reason"] = "site_adjusted_block_to_warn"
            decision["site_adjustment"] = "block_to_warn"
        else:
            decision["site_adjustment"] = "none"
        return decision

    if mode == "monitor":
        if decision.get("action") in ["block", "warn"]:
            pattern_hits = decision.get("pattern_hits", []) or []
            hard_types = {"api_key", "bearer_token", "password", "env_secret", "private_key", "pan", "aadhaar"}
            pattern_types = {hit.get("type", "") for hit in pattern_hits}

            if pattern_types & hard_types:
                decision["site_adjustment"] = "none_hard_block"
                return decision

            decision["action"] = "allow"
            decision["allowed"] = True
            decision["reason"] = "site_adjusted_to_monitor"
            decision["site_adjustment"] = "warn_or_block_to_allow"
        else:
            decision["site_adjustment"] = "none"
        return decision

    decision["site_adjustment"] = "none"
    return decision