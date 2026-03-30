import re

PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone": r"\b\d{10}\b",
    "api_key": r"(sk-[A-Za-z0-9]{20,})",
    "bearer_token": r"(Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*)",
    "password": r"(password\s*=\s*\S+)",
    "env_secret": r"(API_KEY|SECRET_KEY|ACCESS_TOKEN)\s*=\s*\S+",
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "private_key": r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"
}


def detect_sensitive_patterns(text: str):
    matches = []

    for name, pattern in PATTERNS.items():
        found = re.findall(pattern, text, re.IGNORECASE)
        if found:
            matches.append({
                "type": name,
                "matches": found[:3]
            })

    return matches