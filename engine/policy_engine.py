import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from engine.pattern_detector import detect_sensitive_patterns, calculate_pattern_score
from engine.context_detector import calculate_context_score
from engine.fuzzy_detector import calculate_fuzzy_score
from engine.redactor import redact_text
from engine.role_engine import get_user_role, adjust_decision_by_role
from engine.site_policy_engine import adjust_decision_by_site

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = BASE_DIR / "data" / "rules.json"

with open(RULES_PATH, "r", encoding="utf-8") as f:
    rules = json.load(f)

rule_texts = []
for rule in rules:
    parts = [rule.get("title", ""), rule.get("description", "")]
    parts.extend(rule.get("examples", []))
    rule_texts.append("\n".join(parts))

vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2))
rule_matrix = vectorizer.fit_transform(rule_texts)

HARD_BLOCK_PATTERNS = {
    "api_key", "bearer_token", "password",
    "env_secret", "private_key", "pan", "aadhaar"
}


def find_best_rule(text: str):
    vec = vectorizer.transform([text])
    scores = cosine_similarity(vec, rule_matrix)[0]
    idx = int(scores.argmax())
    return rules[idx], float(scores[idx])


def calculate_semantic_score(similarity: float, has_context: bool) -> int:
    if not has_context:
        return int(similarity * 20)
    return int(similarity * 50)


def decide_action(risk: int) -> str:
    if risk < 12:
        return "allow"
    if risk < 52:
        return "warn"
    return "block"


def finalize(decision: dict, user: str, source: str):
    role = get_user_role(user)
    decision = adjust_decision_by_role(user, role, decision)
    decision = adjust_decision_by_site(source, decision)
    return decision


def decide_on_text(text: str, user: str = "unknown", source: str = "unknown"):
    patterns = detect_sensitive_patterns(text)
    pattern_score = calculate_pattern_score(patterns)
    pattern_types = {p["type"] for p in patterns}
    redacted = redact_text(text)

    if pattern_types & HARD_BLOCK_PATTERNS:
        decision = {
            "allowed": False,
            "action": "block",
            "reason": "hard_pattern",
            "message": "Sensitive data detected.",
            "matched_rule": {
                "id": "pattern-detection",
                "title": "Sensitive Pattern Detection",
                "type": "dont",
                "severity": "high",
                "similarity": 1.0
            },
            "pattern_hits": patterns,
            "pattern_score": pattern_score,
            "semantic_score": 0.0,
            "context_score": 0,
            "fuzzy_score": 0,
            "risk_score": 90,
            "redaction_available": redacted != text,
            "redacted_text": redacted if redacted != text else "",
            "user": user,
            "text": text
        }
        return finalize(decision, user, source)

    rule, sim = find_best_rule(text)
    context_score = calculate_context_score(text)
    fuzzy_score = calculate_fuzzy_score(text)
    semantic_score = calculate_semantic_score(sim, context_score > 0)

    risk = min(pattern_score + context_score + fuzzy_score + semantic_score, 100)
    action = decide_action(risk)

    decision = {
        "allowed": action == "allow",
        "action": action,
        "reason": "hybrid",
        "message": rule.get("user_message", "Policy decision generated."),
        "matched_rule": {
            "id": rule.get("id", ""),
            "title": rule.get("title", "Matched Policy Rule"),
            "type": rule.get("type", "unknown"),
            "severity": rule.get("severity", "medium"),
            "similarity": sim
        },
        "pattern_hits": patterns,
        "pattern_score": pattern_score,
        "semantic_score": sim,
        "context_score": context_score,
        "fuzzy_score": fuzzy_score,
        "risk_score": risk,
        "redaction_available": redacted != text,
        "redacted_text": redacted if redacted != text else "",
        "user": user,
        "text": text
    }

    return finalize(decision, user, source)