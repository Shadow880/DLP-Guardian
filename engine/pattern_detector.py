import re

PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone": r"\b\d{10}\b",
    "api_key": r"sk-[A-Za-z0-9]{20,}",
    "bearer_token": r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*",
    "password": r"(?i)(password|passwd|passcode)\s*[:=]?\s*\S+",
    "env_secret": r"(API_KEY|SECRET_KEY|ACCESS_TOKEN)\s*=\s*\S+",
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "private_key": r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"
}

PATTERN_WEIGHTS = {
    "email": 10,
    "phone": 10,
    "api_key": 40,
    "bearer_token": 40,
    "password": 35,
    "env_secret": 35,
    "pan": 25,
    "aadhaar": 25,
    "private_key": 50,
}


def detect_sensitive_patterns(text: str):
    matches = []
    text_l = text.lower()

    for name, pattern in PATTERNS.items():
        found = re.findall(pattern, text, re.IGNORECASE)

        if found:
            normalized = found[:3]

            if normalized and isinstance(normalized[0], tuple):
                normalized = ["".join(x) for x in normalized]

            matches.append({
                "type": name,
                "matches": normalized,
                "weight": PATTERN_WEIGHTS.get(name, 10)
            })

    password_triggers = ["password", "passwd", "passcode", " pass ", "pass="]
    if any(t in f" {text_l} " for t in password_triggers) and not any(m["type"] == "password" for m in matches):
        matches.append({
            "type": "password",
            "matches": ["password-like keyword detected"],
            "weight": PATTERN_WEIGHTS["password"]
        })

    return matches


def calculate_pattern_score(pattern_hits: list) -> int:
    if not pattern_hits:
        return 0

    total = sum(int(hit.get("weight", 0)) for hit in pattern_hits)
    return min(total, 100)