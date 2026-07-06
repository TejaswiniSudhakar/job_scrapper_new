import re
import json
import numpy as np
import joblib
from sentence_transformers import SentenceTransformer
from config import APP_CONFIG

# ==============================
# CONFIG
# ==============================
CANDIDATE_CONFIG = APP_CONFIG["candidate"]
RANKING_CONFIG = APP_CONFIG["ranking"]

EXPECTED_MIN_SALARY = RANKING_CONFIG["expected_min_salary"]
EXPECTED_MAX_SALARY = RANKING_CONFIG["expected_max_salary"]

CANDIDATE_EXPERIENCE_YEARS = CANDIDATE_CONFIG["experience_years"]
KEY_SKILLS = CANDIDATE_CONFIG["key_skills"]
SKILL_WEIGHTS = CANDIDATE_CONFIG["skill_weights"]
RESUME_SUMMARY = CANDIDATE_CONFIG["resume_summary"]

# ==============================
# LOCAL EMBEDDING MODEL
# ==============================
embedding_model = None
resume_embedding = None
ranking_model = None

# ==============================
# INIT
# ==============================
def init():
    global embedding_model
    global resume_embedding
    global ranking_model

    print("Loading embedding model...")

    embedding_model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    resume_embedding = embedding_model.encode(
        RESUME_SUMMARY,
        normalize_embeddings=True
    )

    try:
        ranking_model = joblib.load("job_rank_model.pkl")
        print("Loaded trained ranking model")
    except:
        ranking_model = None
        print("No trained model found")

# ==============================
# EMBEDDINGS
# ==============================
def get_embedding(text):
    if embedding_model is None:
        init()

    return embedding_model.encode(
        text[:5000],
        normalize_embeddings=True
    )

def cosine_similarity(a, b):
    return float(np.dot(a, b))

# ==============================
# SALARY PARSER
# ==============================
def extract_salary(text):
    text = str(text).lower()

    text = (
        text.replace(",", "")
        .replace("₹", "")
        .replace("rs.", "")
        .replace("rs", "")
    )

    match = re.search(
        r"(\d+)\s*[-to]+\s*(\d+)\s*(lpa|lakhs?)",
        text
    )

    if match:
        return (
            (int(match.group(1)) +
             int(match.group(2))) / 2
        ) * 100000

    match = re.search(
        r"(\d+)\s*(lpa|lakhs?)",
        text
    )

    if match:
        return int(match.group(1)) * 100000

    nums = re.findall(r"\d{6,}", text)

    if nums:
        return max(int(x) for x in nums)

    return None

# ==============================
# SALARY SCORE
# ==============================
def salary_score(text):

    salary = extract_salary(text)

    if salary is None:
        return 5

    if salary >= EXPECTED_MAX_SALARY:
        return 10

    if salary >= EXPECTED_MIN_SALARY:
        return 8

    if salary >= EXPECTED_MIN_SALARY * 0.7:
        return 6

    return 3

# ==============================
# EXPERIENCE SCORE
# ==============================
# Sanity bound for a "years of experience" requirement. Anything outside
# this range is almost certainly a parsing artifact or a typo from the
# source posting, not a real requirement.
MAX_PLAUSIBLE_EXPERIENCE_YEARS = 25

def experience_fit_score(exp_text):

    numbers = re.findall(
        r"\d+",
        str(exp_text)
    )

    if not numbers:
        return 5

    numbers = [int(n) for n in numbers]

    # Drop individual numbers that can't plausibly be a years-of-experience
    # figure (e.g. "812 years", "200 years" from a scraping/typo artifact)
    # instead of trusting them or throwing out the whole field.
    plausible = [
        n for n in numbers
        if 0 <= n <= MAX_PLAUSIBLE_EXPERIENCE_YEARS
    ]

    if not plausible:
        return 5

    # A range like "1 - 8 years" means the candidate qualifies once they
    # clear the LOWER bound, not the upper one — someone with 1.3 years
    # fits fine into a "1-8 years" posting. Using min() also naturally
    # handles a single value ("2 years" -> [2]).
    required_exp = min(plausible)

    gap = required_exp - CANDIDATE_EXPERIENCE_YEARS

    if gap >= 3:
        return 1

    if gap >= 2:
        return 3

    if gap >= 1:
        return 7

    return 10

# ==============================
# SKILL SCORE
# ==============================
def skill_match_score(text):

    text = str(text).lower()

    score = 0

    for skill in KEY_SKILLS:

        pattern = r"\b" + re.escape(skill) + r"\b"

        matches = re.findall(
            pattern,
            text
        )

        if matches:

            weight = SKILL_WEIGHTS.get(
                skill,
                1
            )

            freq = min(
                len(matches),
                3
            )

            score += weight * freq

    max_possible = sum(
        SKILL_WEIGHTS.get(skill, 1) * 3
        for skill in KEY_SKILLS
    )

    normalized = (
        score / max_possible
    ) * 10

    return round(
        min(normalized, 10),
        2
    )

# ==============================
# FEATURE EXTRACTION
# ==============================
def extract_features(job):

    job_text = str(
        job.get(
            "job_description",
            ""
        )
    )[:5000]

    job_embedding = get_embedding(
        job_text
    )

    similarity = cosine_similarity(
        resume_embedding,
        job_embedding
    )

    emb_score = similarity * 10

    salary_text = " ".join([
        str(job.get("salary", "")),
        str(job.get("job_title", "")),
        str(job.get("job_description", ""))
    ])

    salary = extract_salary(
        salary_text
    )

    salary = salary or 0

    salary_log = np.log1p(
        salary
    )

    exp_score = experience_fit_score(
        job.get(
            "experience_required",
            ""
        )
    )

    skill_score = skill_match_score(
        job_text
    )

    return [
        emb_score,
        skill_score,
        exp_score,
        salary_log
    ]

# ==============================
# RANK JOB
# ==============================
def rank_job(job):

    features = extract_features(job)

    emb_score = features[0]
    skill_score = features[1]
    exp_score = features[2]

    # fallback score
    pre_score = (
        emb_score * 0.50 +
        skill_score * 0.20 +
        exp_score * 0.30
    )

    if ranking_model:

        try:

            predicted_score = ranking_model.predict(
                [features]
            )[0]

            predicted_score = max(
                0,
                min(
                    10,
                    predicted_score
                )
            )

        except Exception:

            predicted_score = pre_score

    else:

        predicted_score = pre_score

    reason = (
        f"Similarity={emb_score:.1f}, "
        f"Skills={skill_score:.1f}, "
        f"Experience={exp_score:.1f}"
    )

    return (
        round(pre_score, 2),
        round(predicted_score, 2),
        round(predicted_score, 2),
        reason
    )