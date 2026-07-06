import re
import numpy as np
import joblib
from pathlib import Path
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
RESUMES_DIR = Path(APP_CONFIG["files"]["resumes_dir"])

# ==============================
# SCORING WEIGHTS
# Experience is most important, then skill match, then semantic similarity
# ==============================
WEIGHT_EXPERIENCE = 0.50
WEIGHT_SKILLS = 0.30
WEIGHT_EMBEDDING = 0.20

# ==============================
# STATE
# ==============================
embedding_model = None
ranking_model = None
classifier_model = None

# Each resume profile: {"name": str, "text": str, "embedding": ndarray, "skills": set}
resume_profiles = []

# Classifier label mapping
FIT_LABELS = {0: "BAD_FIT", 1: "MAYBE", 2: "GOOD_FIT"}


# ==============================
# RESUME PARSING
# ==============================
def _extract_pdf_text(pdf_path):
    """Extract text from a PDF file. Tries PyPDF2 first, falls back to pdfplumber."""
    try:
        import PyPDF2
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = " ".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text
    except ImportError:
        pass
    except Exception:
        pass

    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = " ".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                return text
    except ImportError:
        pass
    except Exception:
        pass

    print(f"WARNING: Could not extract text from {pdf_path}. Install PyPDF2 or pdfplumber.")
    return ""


def _extract_skills_from_text(text):
    """Extract skills from resume text using a comprehensive skill list.
    Returns a set of lowercase skill strings found in the text."""
    # Common tech skills to look for (lowercase)
    known_skills = [
        "java", "python", "javascript", "typescript", "go", "golang", "rust", "c++", "c#",
        "spring", "spring boot", "springboot", "microservices", "rest", "rest api", "restful",
        "sql", "mysql", "postgresql", "oracle", "pl/sql", "plsql", "mongodb", "redis", "cassandra",
        "aws", "gcp", "azure", "cloud", "docker", "kubernetes", "k8s", "terraform", "ansible",
        "ci/cd", "jenkins", "github actions", "gitlab ci",
        "react", "angular", "vue", "next.js", "nextjs", "node.js", "nodejs", "express",
        "kafka", "rabbitmq", "elasticsearch", "spark", "hadoop", "airflow", "flink",
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
        "pandas", "numpy", "data engineering", "etl", "data pipeline",
        "git", "linux", "agile", "scrum", "jira",
        "selenium", "automation", "web scraping",
        "html", "css", "tailwind",
        "graphql", "grpc", "protobuf",
        "tomcat", "nginx", "apache",
    ]

    text_lower = text.lower()
    found = set()

    for skill in known_skills:
        # Use word boundary matching for short skills to avoid false positives
        if len(skill) <= 3:
            if re.search(r"\b" + re.escape(skill) + r"\b", text_lower):
                found.add(skill)
        else:
            if skill in text_lower:
                found.add(skill)

    return found


def _derive_resume_name(pdf_path):
    """Derive a human-friendly resume name from the filename."""
    stem = pdf_path.stem  # e.g. "Nishant_Backend"
    # Remove the name prefix, keep the role part
    parts = stem.split("_", 1)
    return parts[1] if len(parts) > 1 else stem


# ==============================
# INIT
# ==============================
def init():
    global embedding_model
    global ranking_model
    global classifier_model
    global resume_profiles

    print("Loading embedding model...")
    embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # Load all resume PDFs
    resume_profiles = []
    if RESUMES_DIR.exists():
        pdf_files = sorted(RESUMES_DIR.glob("*.pdf"))
        print(f"Found {len(pdf_files)} resume(s) in {RESUMES_DIR}")

        for pdf_path in pdf_files:
            text = _extract_pdf_text(pdf_path)
            if not text.strip():
                print(f"  Skipping {pdf_path.name} (no text extracted)")
                continue

            embedding = embedding_model.encode(text[:5000], normalize_embeddings=True)
            skills = _extract_skills_from_text(text)
            name = _derive_resume_name(pdf_path)

            resume_profiles.append({
                "name": name,
                "text": text,
                "embedding": embedding,
                "skills": skills,
            })
            print(f"  Loaded: {name} ({len(skills)} skills detected)")
    else:
        print(f"WARNING: Resumes directory not found: {RESUMES_DIR}")

    # Fallback: if no PDFs loaded, use the config resume_summary
    if not resume_profiles:
        print("No PDF resumes loaded. Using config resume_summary as fallback.")
        fallback_text = CANDIDATE_CONFIG["resume_summary"]
        fallback_embedding = embedding_model.encode(fallback_text, normalize_embeddings=True)
        fallback_skills = set(CANDIDATE_CONFIG.get("key_skills", []))
        resume_profiles.append({
            "name": "Default",
            "text": fallback_text,
            "embedding": fallback_embedding,
            "skills": fallback_skills,
        })

    # Load trained models if available
    try:
        model_path = Path(__file__).resolve().parent / "job_rank_model.pkl"
        ranking_model = joblib.load(model_path)
        print("Loaded trained ranking model (regression)")
    except Exception:
        ranking_model = None

    try:
        clf_path = Path(__file__).resolve().parent / "job_classifier_model.pkl"
        classifier_model = joblib.load(clf_path)
        print("Loaded trained classifier model (3-class)")
    except Exception:
        classifier_model = None
        print("No classifier found, using formula-based scoring only")


# ==============================
# EMBEDDINGS
# ==============================
def get_embedding(text):
    if embedding_model is None:
        init()
    return embedding_model.encode(text[:5000], normalize_embeddings=True)


def cosine_similarity(a, b):
    return float(np.dot(a, b))


# ==============================
# SALARY PARSER
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

    nums = re.findall(r"\d{6,}", text)
    if nums:
        return max(int(x) for x in nums)

    return None


# ==============================
# EXPERIENCE SCORE (most important factor)
# ==============================
MAX_PLAUSIBLE_EXPERIENCE_YEARS = 25


def experience_fit_score(exp_text):
    """Score 0-10 based on how well the candidate's experience matches the requirement.
    This is the DOMINANT scoring factor."""
    numbers = re.findall(r"\d+", str(exp_text))
    if not numbers:
        return 7  # No requirement stated = slightly favorable

    numbers = [int(n) for n in numbers]
    plausible = [n for n in numbers if 0 <= n <= MAX_PLAUSIBLE_EXPERIENCE_YEARS]
    if not plausible:
        return 7

    # Use the minimum of the range as the requirement threshold
    required_exp = min(plausible)
    gap = required_exp - CANDIDATE_EXPERIENCE_YEARS

    if gap >= 4:
        return 0  # Way too senior
    if gap >= 3:
        return 1
    if gap >= 2:
        return 3
    if gap >= 1:
        return 5
    if gap >= 0:
        return 8  # Exactly at threshold
    # Candidate exceeds requirement
    return 10


# ==============================
# SKILL MATCH SCORE (binary: skill present or not)
# ==============================
def skill_match_score(job_text, resume_skills):
    """Score 0-10 based on what fraction of the resume's skills appear in the job.
    Binary matching: each skill is either found (1) or not (0). No frequency weighting."""
    if not resume_skills:
        return 5

    job_text_lower = job_text.lower()
    matched = 0

    for skill in resume_skills:
        if len(skill) <= 3:
            if re.search(r"\b" + re.escape(skill) + r"\b", job_text_lower):
                matched += 1
        else:
            if skill in job_text_lower:
                matched += 1

    # Score = fraction of resume skills found in job * 10
    return round(min((matched / len(resume_skills)) * 10, 10), 2)


# ==============================
# SCORE JOB AGAINST ONE RESUME
# ==============================
def _score_against_resume(job_text, job_embedding, exp_text, resume_profile):
    """Score a job against a single resume profile. Returns (total_score, breakdown)."""
    emb_score = cosine_similarity(resume_profile["embedding"], job_embedding) * 10
    skill_score = skill_match_score(job_text, resume_profile["skills"])
    exp_score = experience_fit_score(exp_text)

    total = (
        emb_score * WEIGHT_EMBEDDING +
        skill_score * WEIGHT_SKILLS +
        exp_score * WEIGHT_EXPERIENCE
    )

    return total, {
        "emb_score": emb_score,
        "skill_score": skill_score,
        "exp_score": exp_score,
    }


# ==============================
# FEATURE EXTRACTION
# ==============================
def extract_features(job):
    """Extract numeric features for the ML model.
    Uses the best-matching resume for embedding and skill scores."""
    job_text = str(job.get("job_description", ""))[:5000]
    job_embedding = get_embedding(job_text)
    exp_text = job.get("experience_required", "")

    # Find best resume match
    best_score = -1
    best_breakdown = None

    for profile in resume_profiles:
        score, breakdown = _score_against_resume(job_text, job_embedding, exp_text, profile)
        if score > best_score:
            best_score = score
            best_breakdown = breakdown

    if best_breakdown is None:
        # Fallback if no profiles loaded
        return [0, 0, 5, 0]

    salary_text = " ".join([
        str(job.get("salary", "")),
        str(job.get("job_title", "")),
        job_text
    ])
    salary = extract_salary(salary_text) or 0
    salary_log = np.log1p(salary)

    return [
        best_breakdown["emb_score"],
        best_breakdown["skill_score"],
        best_breakdown["exp_score"],
        salary_log,
    ]


# ==============================
# RANK JOB
# ==============================
def rank_job(job):
    """Rank a job against all resumes. Returns (pre_score, gpt_score, final_score, reason).
    The job is scored against each resume and the best match wins."""
    job_text = str(job.get("job_description", ""))[:5000]
    job_embedding = get_embedding(job_text)
    exp_text = job.get("experience_required", "")

    # Score against all resumes, pick the best
    best_score = -1
    best_breakdown = None
    best_resume_name = "Unknown"

    for profile in resume_profiles:
        score, breakdown = _score_against_resume(job_text, job_embedding, exp_text, profile)
        if score > best_score:
            best_score = score
            best_breakdown = breakdown
            best_resume_name = profile["name"]

    if best_breakdown is None:
        return (0, 0, 0, "No resume profiles loaded")

    emb_score = best_breakdown["emb_score"]
    skill_score = best_breakdown["skill_score"]
    exp_score = best_breakdown["exp_score"]

    pre_score = (
        emb_score * WEIGHT_EMBEDDING +
        skill_score * WEIGHT_SKILLS +
        exp_score * WEIGHT_EXPERIENCE
    )

    # Use classifier if available, otherwise fall back to formula
    fit_label = "UNKNOWN"
    final_score = pre_score

    if classifier_model:
        try:
            from services.feature_extractor import extract_classification_features
            features = extract_classification_features(job)
            pred_class = classifier_model.predict([features])[0]
            proba = classifier_model.predict_proba([features])[0]
            fit_label = FIT_LABELS.get(pred_class, "UNKNOWN")
            confidence = float(proba[pred_class])

            # Only override formula score when classifier is confident
            if confidence >= 0.6:
                if pred_class == 2:  # GOOD_FIT
                    final_score = max(pre_score, 7.5 + confidence)
                elif pred_class == 0:  # BAD_FIT
                    final_score = min(pre_score, 5.5 - confidence)
            # Low confidence or MAYBE -> keep pre_score
        except Exception:
            final_score = pre_score
    elif ranking_model:
        try:
            salary_text = " ".join([
                str(job.get("salary", "")),
                str(job.get("job_title", "")),
                job_text
            ])
            salary_log = np.log1p(extract_salary(salary_text) or 0)
            features = [emb_score, skill_score, exp_score, salary_log]
            final_score = float(np.clip(ranking_model.predict([features])[0], 0, 10))
        except Exception:
            final_score = pre_score

    reason = (
        f"Fit={fit_label}, BestResume={best_resume_name}, "
        f"Experience={exp_score:.1f}, "
        f"Skills={skill_score:.1f}, "
        f"Similarity={emb_score:.1f}"
    )

    return (
        round(pre_score, 2),
        round(final_score, 2),
        round(final_score, 2),
        reason,
    )
