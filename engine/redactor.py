import re


def mask_email(text: str) -> str:
    def repl(match):
        email = match.group(0)
        parts = email.split("@")
        name = parts[0]
        domain = parts[1]
        if len(name) <= 2:
            masked_name = name[0] + "*"
        else:
            masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
        return f"{masked_name}@{domain}"
    return re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", repl, text)


def mask_phone(text: str) -> str:
    def repl(match):
        s = re.sub(r"\D", "", match.group(0))
        if len(s) == 10:
            return s[:2] + "******" + s[-2:]
        return "[REDACTED_PHONE]"
    return re.sub(r"\b\d{10}\b", repl, text)


def mask_api_key(text: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9]{20,}", "sk-[REDACTED]", text, flags=re.IGNORECASE)


def mask_bearer_token(text: str) -> str:
    return re.sub(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", "Bearer [REDACTED]", text, flags=re.IGNORECASE)


def mask_password(text: str) -> str:
    return re.sub(r"(password\s*=\s*)\S+", r"\1[REDACTED]", text, flags=re.IGNORECASE)


def mask_env_secret(text: str) -> str:
    return re.sub(
        r"(API_KEY|SECRET_KEY|ACCESS_TOKEN)\s*=\s*\S+",
        lambda m: f"{m.group(1)}=[REDACTED]",
        text,
        flags=re.IGNORECASE
    )


def mask_pan(text: str) -> str:
    return re.sub(r"\b([A-Z]{5})([0-9]{4})([A-Z])\b", r"\1****\3", text)


def mask_aadhaar(text: str) -> str:
    def repl(match):
        s = re.sub(r"\s", "", match.group(0))
        return f"{s[:4]} XXXX {s[-4:]}"
    return re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", repl, text)


def mask_private_key(text: str) -> str:
    return re.sub(
        r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----.*?-----END (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----",
        "[REDACTED_PRIVATE_KEY]",
        text,
        flags=re.DOTALL
    )


def redact_text(text: str) -> str:
    redacted = text
    redacted = mask_email(redacted)
    redacted = mask_phone(redacted)
    redacted = mask_api_key(redacted)
    redacted = mask_bearer_token(redacted)
    redacted = mask_password(redacted)
    redacted = mask_env_secret(redacted)
    redacted = mask_pan(redacted)
    redacted = mask_aadhaar(redacted)
    redacted = mask_private_key(redacted)
    return redacted