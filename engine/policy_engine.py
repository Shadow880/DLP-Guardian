import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from engine.pattern_detector import detect_sensitive_patterns

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "rules.json"

with open(RULES_PATH, "r", encoding="utf-8") as f:
    rules = json.load(f)

rule_texts = []
for rule in rules:
    parts = [rule["title"], rule["description"]]
    parts.extend(rule.get("examples", []))
    full_text = "\n".join(parts)
    rule_texts.append(full_text)

vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2))
rule_matrix = vectorizer.fit_transform(rule_texts)

HIGH_SIM = 0.20
MED_SIM = 0.10


def find_best_rule(user_text: str, top_k: int = 3):
    query_vec = vectorizer.transform([user_text])
    scores = cosine_similarity(query_vec, rule_matrix)[0]

    ranked_indices = scores.argsort()[::-1][: min(top_k, len(rules))]

    matches = []
    for idx in ranked_indices:
        rule = rules[int(idx)]
        matches.append({
            "rule": rule,
            "score": float(scores[idx])
        })
    return matches


def decide_on_text(user_text: str):
    pattern_hits = detect_sensitive_patterns(user_text)
    top_matches = find_best_rule(user_text, top_k=3)

    if pattern_hits:
        return {
            "allowed": False,
            "action": "block",
            "reason": "pattern_detected",
            "matched_rule": {
                "id": "pattern-detection",
                "title": "Sensitive Pattern Detection",
                "type": "dont",
                "severity": "high",
                "similarity": 1.0
            },
            "message": "Sensitive data pattern detected in the prompt.",
            "pattern_hits": pattern_hits,
            "detection_source": "pattern"
        }

    if not top_matches:
        return {
            "allowed": True,
            "action": "allow",
            "reason": "no_rules",
            "matched_rule": None,
            "message": "No policy rules defined. Allowed by default.",
            "pattern_hits": [],
            "detection_source": "none"
        }

    best = top_matches[0]
    rule = best["rule"]
    score = best["score"]

    rule_type = rule.get("type", "unknown")
    severity = rule.get("severity", "low")

    decision = {
        "matched_rule": {
            "id": rule["id"],
            "title": rule["title"],
            "type": rule_type,
            "severity": severity,
            "similarity": score
        },
        "pattern_hits": [],
        "detection_source": "semantic"
    }

    if score < MED_SIM:
        decision.update({
            "allowed": True,
            "action": "allow",
            "reason": "low_similarity",
            "message": "No strong policy match. Allowed, but should be monitored."
        })
        return decision

    if rule_type == "dont":
        if score >= HIGH_SIM:
            decision.update({
                "allowed": False,
                "action": "block",
                "reason": "matched_dont_high",
                "message": rule.get("user_message", "This action is not allowed.")
            })
        else:
            decision.update({
                "allowed": False,
                "action": "warn",
                "reason": "matched_dont_medium",
                "message": rule.get("user_message", "This may violate policy. Proceed with caution.")
            })

    elif rule_type == "warn":
        decision.update({
            "allowed": False,
            "action": "warn",
            "reason": "matched_warn",
            "message": rule.get("user_message", "This may contain sensitive information. Proceed with caution.")
        })

    elif rule_type == "do":
        decision.update({
            "allowed": True,
            "action": "allow",
            "reason": "matched_do",
            "message": rule.get("user_message", "This action is allowed under current policy.")
        })

    else:
        decision.update({
            "allowed": True,
            "action": "allow",
            "reason": "unknown_rule_type",
            "message": "Rule type unknown; allowing."
        })

    return decision


if __name__ == "__main__":
    sample_text = "Here is a customer contract with confidential pricing. Please summarize it."
    print(decide_on_text(sample_text))