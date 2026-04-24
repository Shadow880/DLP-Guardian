import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
USER_ROLES_PATH = BASE_DIR / "data" / "user_roles.json"

DEFAULT_ROLE = "employee"
VALID_ROLES = ["employee", "manager", "admin", "hr"]


def load_user_roles():
    if not USER_ROLES_PATH.exists():
        return {}

    try:
        with open(USER_ROLES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_user_roles(user_roles: dict):
    USER_ROLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_ROLES_PATH, "w", encoding="utf-8") as f:
        json.dump(user_roles, f, indent=2)


def get_user_role(user: str) -> str:
    user_roles = load_user_roles()
    role = user_roles.get(user, DEFAULT_ROLE)
    return role if role in VALID_ROLES else DEFAULT_ROLE


def set_user_role(user: str, role: str):
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    user_roles = load_user_roles()
    user_roles[user] = role
    save_user_roles(user_roles)


def adjust_decision_by_role(user: str, role: str, decision: dict) -> dict:
    action = decision.get("action", "allow")
    text = str(decision.get("text", "")).lower()
    matched_rule = decision.get("matched_rule") or {}
    rule_title = str(matched_rule.get("title", "")).lower()
    pattern_hits = decision.get("pattern_hits", []) or []
    pattern_types = {hit.get("type", "") for hit in pattern_hits}
    risk_score = int(decision.get("risk_score", 0))

    hard_block_patterns = {
        "api_key",
        "bearer_token",
        "password",
        "env_secret",
        "private_key",
        "pan",
        "aadhaar",
    }

    sensitive_business_terms = [
        "pricing", "contract", "proposal", "confidential", "financial",
        "forecast", "budget", "customer data", "client data", "dataset"
    ]

    internal_terms = [
        "internal", "business", "strategy", "meeting", "project", "summary",
        "discussion", "brainstorm", "notes"
    ]

    hr_terms = [
        "salary", "employee", "payroll", "compensation", "hr", "hiring",
        "promotion", "appraisal", "bonus", "revision"
    ]

    full_context = f"{text} {rule_title}".strip()

    # Never downgrade hard secrets / regulated IDs
    if pattern_types & hard_block_patterns:
        decision["role"] = role
        decision["role_adjustment"] = "none_hard_block"
        return decision

    has_internal = any(term in full_context for term in internal_terms)
    has_hr = any(term in full_context for term in hr_terms)
    has_sensitive_business = any(term in full_context for term in sensitive_business_terms)

    # HR role: stricter on HR content
    if role == "hr":
        if has_hr:
            if action == "allow":
                decision["action"] = "warn"
                decision["allowed"] = False
                decision["reason"] = "role_adjusted_hr_stricter"
                decision["role_adjustment"] = "allow_to_warn"
            elif action == "warn":
                decision["action"] = "block"
                decision["allowed"] = False
                decision["reason"] = "role_adjusted_hr_stricter"
                decision["role_adjustment"] = "warn_to_block"
            else:
                decision["role_adjustment"] = "none"
        else:
            decision["role_adjustment"] = "none"

    # Manager: relax internal business content, and HR content only one step
    elif role == "manager":
        if has_hr and action == "block" and risk_score < 90:
            decision["action"] = "warn"
            decision["allowed"] = False
            decision["reason"] = "role_adjusted_manager_hr_relaxed"
            decision["role_adjustment"] = "block_to_warn"
        elif action == "block" and has_internal and not has_sensitive_business and not has_hr:
            decision["action"] = "warn"
            decision["allowed"] = False
            decision["reason"] = "role_adjusted_manager_relaxed"
            decision["role_adjustment"] = "block_to_warn"
        elif action == "warn" and has_internal and not has_sensitive_business and not has_hr and risk_score < 55:
            decision["action"] = "allow"
            decision["allowed"] = True
            decision["reason"] = "role_adjusted_manager_relaxed"
            decision["role_adjustment"] = "warn_to_allow"
        else:
            decision["role_adjustment"] = "none"

    # Admin: allow more flexibility, including HR content one step down
    elif role == "admin":
        if has_hr and action == "block" and risk_score < 90:
            decision["action"] = "warn"
            decision["allowed"] = False
            decision["reason"] = "role_adjusted_admin_hr_relaxed"
            decision["role_adjustment"] = "block_to_warn"
        elif action == "block" and has_internal and not has_sensitive_business and not has_hr and risk_score < 70:
            decision["action"] = "warn"
            decision["allowed"] = False
            decision["reason"] = "role_adjusted_admin_relaxed"
            decision["role_adjustment"] = "block_to_warn"
        elif action == "warn" and has_internal and not has_sensitive_business and not has_hr:
            decision["action"] = "allow"
            decision["allowed"] = True
            decision["reason"] = "role_adjusted_admin_relaxed"
            decision["role_adjustment"] = "warn_to_allow"
        else:
            decision["role_adjustment"] = "none"

    # Employee: strict default
    else:
        decision["role_adjustment"] = "none"

    decision["role"] = role
    return decision