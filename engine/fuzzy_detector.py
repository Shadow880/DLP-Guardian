from rapidfuzz import fuzz

FUZZY_TERMS = [
    "client", "customer", "data", "pricing", "contract", "salary",
    "confidential", "password", "passwd", "passcode", "api", "key",
    "payroll", "appraisal", "budget", "financial", "employee", "dataset",
    "internal", "strategy", "legal", "agreement", "procurement", "nda",
    "forecast", "revenue", "compensation", "grievance", "identity"
]
def normalise_evasion(text: str) -> str:
    """Normalise common character substitutions used to evade detection."""
    replacements = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a',
        '5': 's', '@': 'a', '$': 's', '!': 'i',
        '+': 't', '&': 'and'
    }
    result = text.lower()
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    return result

def calculate_fuzzy_score(text: str) -> int:
    normalised = normalise_evasion(text)
    words_original = text.lower().split()
    words_normalised = normalised.split()
    # use union of both so genuine words aren't lost
    words = list(set(words_original + words_normalised))
    score = 0
    for w in words:
        for term in FUZZY_TERMS:
            if fuzz.ratio(w, term) >= 80 and w != term:
                score += 5
    return min(score, 20)