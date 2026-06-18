import re
import json
from urllib import response
import numpy as np
import os
from config import APP_CONFIG
from dotenv import load_dotenv
from openai import OpenAI

# ==============================
# LOAD ENV
# ==============================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==============================
# CONFIGURATION
# ==============================
CANDIDATE_CONFIG = APP_CONFIG["candidate"]
RANKING_CONFIG = APP_CONFIG["ranking"]

EXPECTED_MIN_SALARY = RANKING_CONFIG["expected_min_salary"]
EXPECTED_MAX_SALARY = RANKING_CONFIG["expected_max_salary"]
CANDIDATE_EXPERIENCE_YEARS = CANDIDATE_CONFIG["experience_years"]
KEY_SKILLS = CANDIDATE_CONFIG["key_skills"]
SKILL_WEIGHTS = CANDIDATE_CONFIG["skill_weights"]
RESUME_SUMMARY = CANDIDATE_CONFIG["resume_summary"]

resume_embedding = None


# ==============================
# INIT (call once at startup)
# ==============================
def init():
    global resume_embedding
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=RESUME_SUMMARY
    )
    resume_embedding = response.data[0].embedding


# ==============================
# EMBEDDING FUNCTIONS
# ==============================
def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return response.data[0].embedding


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ==============================
# SALARY PARSER (IMPROVED)
# ==============================
def extract_salary(text):
    text = str(text).lower()
    text = text.replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "")

    match = re.search(r"(\d+)\s*[-to]+\s*(\d+)\s*(lpa|lakhs?)", text)
    if match:
        return ((int(match.group(1)) + int(match.group(2))) / 2) * 100000

    match = re.search(r"(\d+)\s*(lpa|lakhs?)", text)
    if match:
        return int(match.group(1)) * 100000

    match = re.search(r"(\d{5,})\s*[-to]+\s*(\d{5,})", text)
    if match:
        return (int(match.group(1)) + int(match.group(2))) / 2

    nums = re.findall(r"\d{6,}", text)
    if nums:
        return max(int(n) for n in nums)

    return None


def salary_score(text):
    salary = extract_salary(text)

    if salary is None:
        return 5

    if salary >= EXPECTED_MAX_SALARY:
        return 10
    elif salary >= EXPECTED_MIN_SALARY:
        return 8
    elif salary >= EXPECTED_MIN_SALARY * 0.7:
        return 6
    return 3


# ==============================
# EXPERIENCE SCORING (RELAXED)
# ==============================
def experience_fit_score(exp_text):
    numbers = re.findall(r"\d+", str(exp_text))
    if not numbers:
        return 5

    gap = int(numbers[0]) - CANDIDATE_EXPERIENCE_YEARS

    if gap >= 3:
        return 1
    elif gap >= 2:
        return 3
    elif gap >= 1:
        return 7
    elif gap <= 0:
        return 10
    else:
        return 7


# ==============================
# SKILL MATCH
# ==============================
def skill_match_score(text):
    text = str(text).lower()

    score = 0
    matched_skills = set()

    for skill in KEY_SKILLS:
        # Build regex for exact match (handles spaces too)
        pattern = r'\b' + re.escape(skill) + r'\b'

        matches = re.findall(pattern, text)

        if matches:
            matched_skills.add(skill)

            # weight × frequency (capped per skill)
            weight = SKILL_WEIGHTS.get(skill, 1)
            freq = min(len(matches), 3)  # avoid over-counting

            score += weight * freq

    # Normalize to 0–10
    max_possible = sum(SKILL_WEIGHTS.get(s, 1) * 3 for s in KEY_SKILLS)
    normalized = (score / max_possible) * 10 if max_possible else 0

    return round(min(normalized, 10), 2)


# ==============================
# MAIN RANK FUNCTION
# ==============================
def rank_job(job):

    global resume_embedding

    job_text = str(job.get("job_description", ""))[:6000]

    # ==============================
    # EMBEDDING SCORE
    # ==============================
    try:
        job_embedding = get_embedding(job_text)
        similarity = cosine_similarity(resume_embedding, job_embedding)
        emb_score = ((similarity + 1) / 2) * 10
    except:
        emb_score = 0

    # ==============================
    # OTHER SCORES
    # ==============================
    salary_text = " ".join([
        str(job.get("salary", "")),
        str(job.get("job_description", "")),
        str(job.get("job_title", ""))
    ])

    sal_score = salary_score(salary_text)
    exp_score = experience_fit_score(job.get("experience_required", ""))
    skill_score = skill_match_score(job_text)

    # ==============================
    # PRE-SCORE (TUNED)
    # ==============================
    pre_score = (
        emb_score * 0.50 +
        skill_score * 0.20 +
        sal_score * 0 +
        exp_score * 0.30
    )

    # small boost for strong skill match
    if skill_score >= 8:
        pre_score += 0.5

    pre_score = min(pre_score, 10)

    # ==============================
    # GPT EVALUATION (RELAXED)
    # ==============================
    try:
        prompt = f"""
You are a practical hiring evaluator scoring job relevance.

Candidate Experience: {CANDIDATE_EXPERIENCE_YEARS}

Candidate Profile:
{RESUME_SUMMARY}

Job Title:
{job.get('job_title')}

Required Experience:
{job.get('experience_required')}

Job Description:
{job_text}

Rules:
- Focus on skills and backend relevance
- Reduce score if experience gap is high, but do not overly penalize strong skill matches
- Early-career candidates can still fit roles if tech stack matches well
- Ignore salary/company reputation

Return JSON:
{{
"final_score": integer (0-10),
"reason": "short explanation for the score, focusing on key factors in 50 words or less"
}}
"""

        response = client.chat.completions.create(
            model="gpt-5-mini",
            max_completion_tokens=1000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a practical evaluator."},
                {"role": "user", "content": prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        gpt_score = int(result.get("final_score", 0))
        reason = result.get("reason", "")

    except Exception as e:
        print("GPT Error:", str(e))
        gpt_score = 0
        reason = f"GPT evaluation failed: {e}"
        print(response.choices[0].message)
        print(repr(response.choices[0].message.content))

    # ==============================
    # FINAL SCORE (BALANCED)
    # ==============================
    final_score = (
        pre_score * 0.5 +
        gpt_score * 0.5
    )
    return round(pre_score, 2),gpt_score,round(final_score, 2), reason
