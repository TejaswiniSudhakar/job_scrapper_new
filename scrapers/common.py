"""Shared utilities used by multiple scrapers."""

import re
import time
import random


def get_experience_from_description(job_description):
    """Extract years-of-experience requirement from job description text."""
    try:
        desc = job_description.lower().replace("\u2013", "-")
        patterns = [
            r"(\d+)\s*\+\s*years?",
            r"(\d+)\s*-\s*(\d+)\s*years?",
            r"(\d+)\s*to\s*(\d+)\s*years?",
            r"minimum\s*(\d+)\s*years?",
            r"at least\s*(\d+)\s*years?",
            r"(\d+)\s*years?\s*of\s*experience",
            r"(\d+)\s*\+\s*yrs?",
            r"(\d+)\s*-\s*(\d+)\s*yrs?",
            r"(\d+)\s*to\s*(\d+)\s*yrs?",
            r"minimum\s*(\d+)\s*yrs?",
            r"at least\s*(\d+)\s*yrs?",
            r"(\d+)\s*yrs?\s*of\s*experience",
        ]

        for pattern in patterns:
            match = re.search(pattern, desc)
            if not match:
                continue
            if len(match.groups()) == 2:
                return f"{match.group(1)}-{match.group(2)} years"
            return f"{match.group(1)} years"
        return "Not mentioned"
    except Exception:
        return "Not found"


def random_pause(min_seconds=1.0, max_seconds=3.0):
    """Sleep for a random duration between min and max seconds.
    Also accepts a tuple: random_pause((min, max))."""
    if isinstance(min_seconds, (tuple, list)):
        min_seconds, max_seconds = min_seconds
    time.sleep(random.uniform(min_seconds, max_seconds))
