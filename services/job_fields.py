import re

UNKNOWN_EXPERIENCE_VALUES = {"", "-1", "not mentioned", "experience not found", "not found", "na", "n/a", "none"}

DASH_CHARS = "-??"
SALARY_UNITS = r"k|lacs?|lakhs?|lac|lakh|lpa|pa|p\.a\.|per annum|yearly|annual|annually|/month|per month|monthly|month"
CURRENCY = r"(?:rs\.?|inr|₹)?"


def normalize_job_fields(job):
    text = " ".join(
        str(part or "")
        for part in [
            job.get("salary"),
            job.get("experience_required"),
            job.get("job_title"),
            job.get("company_name"),
            job.get("job_description"),
            job.get("reason"),
        ]
    )

    job["salary"] = extract_salary_label(text) or clean_salary(job.get("salary")) or "Not mentioned"
    job["experience_required"] = extract_experience_label(text, job.get("experience_required"))
    return job


def clean_salary(value):
    if not value:
        return None
    value = str(value).strip()
    if not value or value.lower() in {"not mentioned", "not disclosed", "na", "n/a", "none"}:
        return None
    return value


def extract_salary_label(text):
    normalized = normalize_text(text)
    patterns = [
        rf"(?:salary|ctc|compensation|package|pay)\s*[:\-]?\s*{CURRENCY}\s*(\d[\d,]*(?:\.\d+)?)\s*({SALARY_UNITS})?\s*(?:[{DASH_CHARS}]|to)\s*{CURRENCY}\s*(\d[\d,]*(?:\.\d+)?)\s*({SALARY_UNITS})?",
        rf"{CURRENCY}\s*(\d[\d,]*(?:\.\d+)?)\s*({SALARY_UNITS})\s*(?:[{DASH_CHARS}]|to)\s*{CURRENCY}\s*(\d[\d,]*(?:\.\d+)?)\s*({SALARY_UNITS})",
        rf"(?:salary|ctc|compensation|package|pay)\s*[:\-]?\s*{CURRENCY}\s*(\d[\d,]*(?:\.\d+)?)\s*({SALARY_UNITS})",
        rf"{CURRENCY}\s*(\d{{5,}}[\d,]*)\s*(?:[{DASH_CHARS}]|to)\s*{CURRENCY}\s*(\d{{5,}}[\d,]*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.I)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 4:
            return format_salary(groups[0], groups[1], groups[2], groups[3])
        if len(groups) == 2 and re.search(r"\d{5,}", groups[0] or ""):
            return f"?{clean_number(groups[0])}-?{clean_number(groups[1])} PA"
        if len(groups) == 2:
            return format_salary(groups[0], groups[1], None, None)

    return None


def format_salary(min_value, min_unit=None, max_value=None, max_unit=None):
    unit = normalize_salary_unit(max_unit or min_unit or "")
    left = f"{clean_number(min_value)}{(' ' + unit) if unit else ''}"
    if not max_value:
        return left
    right = f"{clean_number(max_value)}{(' ' + unit) if unit else ''}"
    return f"{left}-{right}"


def normalize_salary_unit(unit):
    normalized = str(unit or "").lower().replace(".", "")
    if normalized == "k":
        return "k/month"
    if normalized in {"lac", "lacs", "lakh", "lakhs", "lpa"}:
        return "LPA"
    if "month" in normalized:
        return "/month"
    if normalized in {"pa", "per annum", "yearly", "annual", "annually"}:
        return "PA"
    return ""


def clean_number(value):
    raw = str(value).replace(",", "").strip()
    return raw[:-2] if raw.endswith(".0") else raw


def extract_experience_label(text, existing=None):
    cleaned_existing = str(existing or "").strip()
    if cleaned_existing.lower() not in UNKNOWN_EXPERIENCE_VALUES:
        return format_experience(cleaned_existing)

    normalized = normalize_text(text)
    patterns = [
        rf"(?:experience|exp|minimum|min\.?|at least|required|requires?|preferred|desired|work ex|work experience)\D{{0,45}}(\d+(?:\.\d+)?)\s*(?:[{DASH_CHARS}]|to)\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        rf"(\d+(?:\.\d+)?)\s*(?:[{DASH_CHARS}]|to)\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp|work ex)",
        rf"(?:experience|exp|minimum|min\.?|at least|required|requires?|preferred|desired|work ex|work experience)\D{{0,45}}(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        rf"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp|work ex)",
        rf"(?:fresher|freshers|entry level|entry-level|graduate trainee)",
    ]

    for index, pattern in enumerate(patterns):
        match = re.search(pattern, normalized, flags=re.I)
        if not match:
            continue
        if index == len(patterns) - 1:
            return "0 years"
        groups = match.groups()
        if len(groups) >= 2:
            return format_experience(f"{groups[0]}-{groups[1]} years")
        return format_experience(f"{groups[0]} years")

    return "Not mentioned"


def format_experience(value):
    numbers = re.findall(r"\d+(?:\.\d+)?", str(value))
    if len(numbers) >= 2:
        return f"{numbers[0]}-{numbers[1]} years"
    if len(numbers) == 1:
        return f"{numbers[0]} years"
    return str(value).strip() or "Not mentioned"


def normalize_text(text):
    return str(text or "").replace("\u00a0", " ").replace("\n", " ").replace("\t", " ").replace("???", "-").replace("???", "-")
