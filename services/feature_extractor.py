"""
Feature extraction for the job fit classifier.

Core features (experience + skills dominate):
    0. exp_score          - Experience fit (0-10) — PRIMARY
    1. skill_score        - Binary skill match (0-10) — PRIMARY
    2. exp_skill_combo    - exp_score * skill_score / 10 — interaction term
    3. emb_score          - Embedding similarity * 10
    4. title_similarity   - Job title vs target roles cosine sim
    5. keyword_overlap    - JD words ∩ resume words / JD words
    6. skill_match_ratio  - candidate_skills_in_jd / jd_total_skills
    7. salary_log         - log1p(parsed salary)
    8. location_match     - 1 if Bengaluru/Remote, else 0
    9. desc_length_log    - log1p(description length)

Design: exp_score and skill_score appear directly AND as an interaction
term, so tree splits on them carry 3x the signal vs other features.
"""

import re
import numpy as np
from config import APP_CONFIG

TARGET_ROLES = APP_CONFIG["scrapers"]["keywords"]
PREFERRED_LOCATIONS = {"bengaluru", "bangalore", "remote", "work from home", "hybrid"}


def _title_similarity(job_title, embedding_model):
    """Cosine similarity between job title and best-matching target role."""
    if not job_title or not job_title.strip():
        return 0.0
    title_emb = embedding_model.encode(job_title, normalize_embeddings=True)
    if not hasattr(_title_similarity, "_role_embs"):
        _title_similarity._role_embs = embedding_model.encode(
            TARGET_ROLES, normalize_embeddings=True
        )
    sims = np.dot(_title_similarity._role_embs, title_emb)
    return float(np.max(sims))


def _keyword_overlap(job_text, resume_text):
    """Fraction of JD meaningful words found in resume."""
    stopwords = {
        "the", "and", "for", "are", "with", "you", "that", "this", "will",
        "have", "from", "they", "been", "has", "was", "were", "can", "our",
        "your", "their", "about", "which", "would", "should", "could", "into",
        "also", "more", "other", "than", "then", "what", "when", "where",
        "who", "how", "all", "each", "every", "both", "few", "most", "some",
        "such", "not", "only", "same", "but", "very", "just", "because",
        "any", "these", "those", "its", "may", "must", "shall", "able",
        "work", "role", "team", "experience", "years", "looking", "join",
        "company", "opportunity", "responsibilities", "requirements",
    }
    jd_words = set(re.findall(r"[a-z]{3,}", job_text.lower())) - stopwords
    if not jd_words:
        return 0.0
    resume_words = set(re.findall(r"[a-z]{3,}", resume_text.lower()))
    return len(jd_words & resume_words) / len(jd_words)


def _skill_match_ratio(job_text, resume_skills):
    """Fraction of JD-mentioned tech skills that candidate has."""
    tech_terms = [
        "java", "python", "javascript", "typescript", "go", "rust", "c++", "c#", "scala", "kotlin",
        "spring", "spring boot", "django", "flask", "fastapi", "express", "node.js",
        "react", "angular", "vue", "next.js",
        "sql", "mysql", "postgresql", "oracle", "mongodb", "redis", "cassandra", "dynamodb",
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible", "jenkins",
        "kafka", "rabbitmq", "elasticsearch", "spark", "hadoop", "airflow",
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "microservices", "rest", "graphql", "grpc", "ci/cd",
        "git", "linux", "agile", "scrum",
    ]
    text_lower = job_text.lower()
    jd_skills = [t for t in tech_terms if t in text_lower]
    if not jd_skills:
        return 0.5
    matched = sum(1 for s in jd_skills if s in resume_skills)
    return matched / len(jd_skills)


def _location_match(location_text):
    if not location_text:
        return 0.5
    loc_lower = str(location_text).lower()
    return 1.0 if any(p in loc_lower for p in PREFERRED_LOCATIONS) else 0.0


def extract_classification_features(job):
    """Extract 10 features. Experience and skills are dominant."""
    from services.ranker import (
        get_embedding, cosine_similarity, experience_fit_score,
        skill_match_score, extract_salary, embedding_model, resume_profiles,
    )

    job_text = str(job.get("job_description", ""))[:5000]
    job_title = str(job.get("job_title", ""))
    exp_text = job.get("experience_required", "")
    location = job.get("location", "")
    salary_raw = " ".join([str(job.get("salary", "")), job_title, job_text])

    job_embedding = get_embedding(job_text)

    # Best resume match
    best_emb = 0.0
    best_skill = 0.0
    best_resume_text = ""
    best_resume_skills = set()

    for profile in resume_profiles:
        emb = cosine_similarity(profile["embedding"], job_embedding) * 10
        skill = skill_match_score(job_text, profile["skills"])
        if emb + skill > best_emb + best_skill:
            best_emb = emb
            best_skill = skill
            best_resume_text = profile["text"]
            best_resume_skills = profile["skills"]

    exp_score = experience_fit_score(exp_text)
    salary = extract_salary(salary_raw) or 0

    # Interaction: exp * skill — amplifies when BOTH are good/bad
    exp_skill_combo = (exp_score * best_skill) / 10.0

    return [
        exp_score,                              # 0 - PRIMARY
        best_skill,                             # 1 - PRIMARY
        exp_skill_combo,                        # 2 - interaction (amplifies core signals)
        best_emb,                               # 3 - embedding
        _title_similarity(job_title, embedding_model),  # 4
        _keyword_overlap(job_text, best_resume_text),   # 5
        _skill_match_ratio(job_text, best_resume_skills),  # 6
        np.log1p(salary),                       # 7
        _location_match(location),              # 8
        np.log1p(len(job_text)),                # 9
    ]
