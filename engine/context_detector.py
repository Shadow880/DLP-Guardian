WEAK_TERMS = {
    "client", "meeting", "internal", "project", "business", "discussion",
    "employee", "staff", "team", "document", "report", "review", "summary",
    "data", "record", "sheet", "file", "analysis", "update", "note"
}

STRONG_PHRASES = {
    # Client / Customer
    "client data": 35,
    "customer data": 35,
    "client dataset": 40,
    "customer dataset": 40,
    "customer proposal": 30,
    "client proposal": 30,
    "client meeting": 20,
    "client feedback": 20,
    "client conversation": 20,
    "client report": 25,
    "client contract": 30,

    "clent": 25,
    "apii": 30,
    "apii key": 40,
    "clent proposal": 35,

    # Financial
    "pricing": 25,
    "pricing data": 30,
    "pricing sheet": 35,
    "pricing document": 30,
    "financial data": 40,
    "financial forecast": 35,
    "budget forecast": 35,
    "budget": 20,
    "cost estimate": 30,
    "margin table": 30,
    "revenue": 20,
    "payroll": 40,
    "payrol": 35,       # typo variant
    "quarterly forecast": 30,

    # HR / Employee
    "salary": 35,
    "employee salary": 40,
    "salary revision": 40,
    "salary sheet": 40,
    "salary compensation": 40,
    "compensation": 25,
    "appraisal": 35,
    "employee appraisal": 40,
    "employee grievance": 35,
    "employee identity": 35,
    "hr communication": 30,
    "hr review": 30,
    "hiring": 20,
    "promotion": 20,
    "bonus": 20,

    # Legal / Contracts
    "contract": 30,
    "nda": 35,
    "legal agreement": 35,
    "vendor agreement": 35,
    "procurement contract": 40,
    "contract clauses": 35,
    "legal risk": 30,
    "legal terms": 25,

    # Confidential / Internal
    "confidential": 30,
    "confidential document": 35,
    "confidential business": 35,
    "confidential strategy": 35,
    "confidential management": 35,
    "confidential legal": 35,
    "strategy note": 30,
    "strategy discussion": 30,
    "management presentation": 30,
    "management review": 30,
    "business plan": 30,
    "internal strategy": 30,
    "internal financial": 35,
    "internal records": 30,
    "internal payroll": 40,
    "internal business": 20,
    "internal hr": 30,

    "internal financial forecast": 50,
    "salary compensation": 50,
    "confidential business plan": 50,
    "cl1ent d@ta": 50,
    "confidantial document": 45,
    "databse export": 45,

    # Source code / Technical
    "source code": 35,
    "api key": 40,
    "secret key": 40,
    "access token": 40,
    "private key": 50,
    "env file": 35,
    "config file": 25,
    "architecture document": 30,

    # Data exports / Datasets
    "database export": 40,
    "data export": 35,
    "records dump": 40,
    "dataset": 30,
    "csv export": 35,
    "customer table": 35,

    "vendor nda": 45,
    "nda agreement": 45,
    "management review deck": 40,
    "management review": 35,
    "cl1ent": 35,       # evasion variant
    "s@lary": 35,       # evasion variant  
    "confidantial": 35,
    "custommer dataset": 40,
    "database export": 40,
    "databse": 30,
    "employe identity": 35,
    "confidentail": 35,
    "cliant": 25,
    "strategy discussion note": 40,
    "client contract": 35,
    "hr communication": 30,


    "pan card": 35,
    "pan number": 35,
    "pan and address": 35,
    "aadhaar": 35,
    "aadhar": 35,
    "internal strategy discussion": 25,
    "internal hr communication": 28,
    "business email": 15,
    "client proposal": 25,

    "internal financial forecast": 55,
    "salary compensation": 55,
    "confidential business plan": 55,

    

    # add 
    "business discussion": 20,
    "internal announcement": 18,
    "internal complaint": 18,
    "vulnerability summary": 25,
    "escalation message": 18,
    "soc alert": 25,
    "incident report": 25,
    "quarterly discussion": 20,
    "follow-up email": 15,
    "project proposal": 18,
    "custommer": 30,    # common typo variant
    "cliant": 25,
    "confidantial": 30,
    "databse": 25,
    "priceing": 25,
    "employe": 30,
    "contarct": 30,
    "finantial": 30,
}

def calculate_context_score(text: str) -> int:
    text_l = text.lower()
    words = text_l.split()
    
    # if "client" appears alone with no sensitive companion words, ignore it
    client_companions = [
        "data", "dataset", "proposal", "contract", "salary",
        "financial", "confidential", "pricing", "record", "export"
    ]
    if "client" in words and not any(c in text_l for c in client_companions):
        # remove client from consideration by working on a cleaned version
        text_l = text_l.replace("client", "")
    # known safe patterns — return 0 immediately
    safe_overrides = [
    "project ideas", "explain what", "what is", "how does",
    "suggest a", "give me ideas", "learning roadmap",
]
    if any(phrase in text.lower() for phrase in safe_overrides):
        return 0
    substitutions = {'0':'o','1':'i','3':'e','4':'a','5':'s','@':'a','$':'s'}
    normalised = text.lower()
    for char, rep in substitutions.items():
        normalised = normalised.replace(char, rep)
    
    # score on both original and normalised
    text_l = text.lower()
    weak = sum(1 for w in WEAK_TERMS if w in text_l or w in normalised)
    strong_orig = sum(score for phrase, score in STRONG_PHRASES.items() if phrase in text_l)
    strong_norm = sum(score for phrase, score in STRONG_PHRASES.items() if phrase in normalised)
    strong = max(strong_orig, strong_norm)
    
  # prevent single-category domination
    if strong > 40 and strong_orig == strong_norm:
        strong = 40
    return min(strong + weak * 3, 60)