"""
ATS-optimized job-specific LaTeX resume generator.

Strategy:
- Mirror exact keywords and phrases from the job description
- Only show skills the JD explicitly asks for (ATS scores keyword matches)
- Rewrite summary to include the job title and key JD terms
- Select and rewrite experience bullets to naturally include JD keywords
- Use clean single-column format (ATS parsers struggle with multi-column)
- No graphics, tables, or fancy formatting (ATS can't parse them)
"""

import re
import subprocess
import hashlib
from pathlib import Path
from config import APP_CONFIG
from services.resume_data import RESUME_DATA

OUTPUT_DIR = Path(APP_CONFIG["files"].get("generated_resumes_dir", Path(__file__).resolve().parent.parent / "generated_resumes"))
CANDIDATE_YEARS = APP_CONFIG["candidate"]["experience_years"]


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _escape_latex(text):
    """Escape special LaTeX characters."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


# ==============================
# JD KEYWORD EXTRACTION
# ==============================

# Comprehensive skill/keyword list for extraction
KNOWN_KEYWORDS = [
    # Languages
    "java", "python", "javascript", "typescript", "go", "golang", "rust", "c++", "c#", "scala", "kotlin", "ruby", "php",
    # Frameworks
    "spring boot", "spring", "spring mvc", "spring cloud", "spring security",
    "microservices", "rest", "restful", "rest api", "graphql", "grpc",
    "django", "flask", "fastapi", "express", "nest.js",
    "react", "angular", "vue", "next.js", "node.js",
    "hibernate", "jpa", "mybatis",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "oracle", "pl/sql", "plsql",
    "mongodb", "redis", "cassandra", "dynamodb", "elasticsearch", "neo4j",
    # Cloud & DevOps
    "aws", "gcp", "google cloud", "azure", "cloud", "serverless", "lambda",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "helm",
    "ci/cd", "jenkins", "github actions", "gitlab ci", "argocd",
    "prometheus", "grafana", "datadog", "splunk",
    # Messaging & Streaming
    "kafka", "rabbitmq", "sqs", "sns", "event-driven", "pub/sub",
    # Data & ML
    "spark", "hadoop", "airflow", "flink", "hive", "presto",
    "etl", "data pipeline", "data warehouse", "data lake",
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
    "pandas", "numpy", "nlp", "computer vision",
    # Tools & Practices
    "git", "linux", "unix", "bash", "shell scripting",
    "agile", "scrum", "jira", "confluence",
    "tdd", "unit testing", "integration testing", "junit", "mockito", "pytest",
    "selenium", "automation", "web scraping",
    "design patterns", "solid", "oop", "object oriented",
    "distributed systems", "high availability", "scalability", "load balancing",
    "api gateway", "service mesh", "istio",
    "oauth", "jwt", "authentication", "authorization", "security",
    "logging", "monitoring", "observability",
    "multithreading", "concurrency", "async",
    "tomcat", "nginx", "apache",
]


def _extract_jd_keywords(job_text):
    """Extract all matching keywords from the job description.
    Returns a set of lowercase keywords found in the JD."""
    text_lower = job_text.lower()
    found = set()
    for kw in KNOWN_KEYWORDS:
        if len(kw) <= 3:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                found.add(kw)
        else:
            if kw in text_lower:
                found.add(kw)
    return found


def _extract_jd_phrases(job_text):
    """Extract important multi-word phrases from JD that should appear in resume.
    These are action-oriented phrases ATS systems look for."""
    text_lower = job_text.lower()
    phrases = []

    patterns = [
        r"(develop(?:ing|ed|ment of)?\s+(?:[\w\s]{3,30}))",
        r"(build(?:ing)?\s+(?:[\w\s]{3,25}))",
        r"(design(?:ing|ed)?\s+(?:[\w\s]{3,25}))",
        r"(implement(?:ing|ed|ation of)?\s+(?:[\w\s]{3,25}))",
        r"(experience (?:with|in)\s+(?:[\w\s,/]{3,40}))",
        r"(proficien(?:t|cy)\s+in\s+(?:[\w\s,/]{3,40}))",
        r"(knowledge of\s+(?:[\w\s,/]{3,40}))",
        r"(familiar(?:ity)?\s+with\s+(?:[\w\s,/]{3,40}))",
        r"(work(?:ing)?\s+with\s+(?:[\w\s]{3,25}))",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        phrases.extend(m.strip()[:60] for m in matches[:3])

    return phrases[:10]


def _extract_job_title_keywords(job_title):
    """Extract role-defining words from the job title for ATS title matching."""
    title_lower = job_title.lower()
    # Remove common filler words
    fillers = {"senior", "junior", "lead", "staff", "principal", "associate", "intern", "i", "ii", "iii", "iv", "at", "in", "for", "-", "–", "/"}
    words = [w for w in re.findall(r"\w+", title_lower) if w not in fillers and len(w) > 2]
    return words


# ==============================
# ATS-OPTIMIZED CONTENT GENERATION
# ==============================

def _build_ats_summary(job_title, jd_keywords, profile_name):
    """Build a summary that mirrors the job title and top JD keywords.
    ATS systems weight the summary heavily for keyword density."""
    data = RESUME_DATA

    # Use the actual job title in the summary (ATS title matching)
    title_clean = re.sub(r"\s*[\(\[].*?[\)\]]", "", job_title).strip()

    # Pick top keywords to weave into summary
    priority_skills = []
    for kw in jd_keywords:
        all_candidate_skills = set()
        for skills in data["skills"].values():
            all_candidate_skills.update(s.lower() for s in skills)
        for exp in data["experience"]:
            all_candidate_skills.update(t.lower() for t in exp.get("tags", []))
        if kw in all_candidate_skills:
            priority_skills.append(kw)

    priority_skills = priority_skills[:10]
    skill_str = ", ".join(s.title() if len(s) > 3 else s.upper() for s in priority_skills[:8])

    # Build a fuller summary with job title, skills, and profile-specific content
    closers = {
        "Backend": (
            "Experienced in building scalable backend services, REST APIs, and distributed systems. "
            "Strong foundation in database optimization, microservices architecture, and enterprise application development. "
            "Hands-on experience with CI/CD automation, containerization, and Agile development practices."
        ),
        "cloud_engineer": (
            "Experienced in cloud infrastructure, containerization, and CI/CD automation. "
            "Strong foundation in infrastructure-as-code, container orchestration, and monitoring. "
            "Hands-on experience with serverless architectures, auto-scaling, and cost optimization."
        ),
        "data_engineer": (
            "Experienced in building data pipelines, ETL workflows, and large-scale data processing. "
            "Strong foundation in data modeling, workflow orchestration, and database optimization. "
            "Hands-on experience with batch processing, data quality management, and analytics engineering."
        ),
        "ML": (
            "Experienced in building and deploying machine learning models in production environments. "
            "Strong foundation in feature engineering, model training, and experiment tracking. "
            "Hands-on experience with NLP, deep learning frameworks, and model serving at scale."
        ),
    }

    summary = (
        f"{title_clean} with {CANDIDATE_YEARS} years of hands-on experience. "
        f"Skilled in {skill_str}. "
        f"{closers.get(profile_name, closers['Backend'])}"
    )

    return summary


def _build_ats_skills_section(jd_keywords):
    """Only show skills that the JD asks for. ATS scores exact keyword matches.
    Skills not in the JD add noise and dilute keyword density."""
    data = RESUME_DATA
    all_skills = data["skills"]

    # Flatten all candidate skills with their categories
    candidate_skills = {}
    for category, skills in all_skills.items():
        for skill in skills:
            candidate_skills[skill.lower()] = (skill, category)

    # Only include skills that appear in JD AND candidate has
    matched = {}
    for kw in jd_keywords:
        if kw in candidate_skills:
            skill_display, category = candidate_skills[kw]
            matched.setdefault(category, []).append(skill_display)

    # If very few matches, add closely related skills from matched categories
    if sum(len(v) for v in matched.values()) < 6:
        for category in matched:
            for skill in all_skills.get(category, []):
                if skill.lower() not in jd_keywords and len(matched.get(category, [])) < 8:
                    matched.setdefault(category, []).append(skill)

    # If still empty, fall back to all skills
    if not matched:
        return all_skills

    return matched


def _score_bullet_for_jd(bullet, jd_keywords):
    """Score a bullet point by how many JD keywords it contains."""
    bullet_lower = bullet.lower()
    return sum(1 for kw in jd_keywords if kw in bullet_lower)


def _select_ats_bullets(bullets, tags, jd_keywords, max_bullets=5):
    """Select bullets that contain the most JD keywords.
    ATS systems scan bullet points for keyword matches."""
    scored = []
    for bullet in bullets:
        score = _score_bullet_for_jd(bullet, jd_keywords)
        # Bonus for tag overlap
        score += len(set(tags) & jd_keywords) * 0.5
        scored.append((score, bullet))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [b for _, b in scored[:max_bullets]]


def _pick_profile(job_text):
    """Pick the best resume profile based on JD content."""
    text_lower = job_text.lower()
    scores = {"Backend": 0, "cloud_engineer": 0, "data_engineer": 0, "ML": 0}

    kw_map = {
        "Backend": ["java", "spring", "microservices", "rest", "api", "backend", "server", "hibernate", "jpa"],
        "cloud_engineer": ["cloud", "aws", "gcp", "azure", "devops", "kubernetes", "docker", "terraform", "sre", "infrastructure"],
        "data_engineer": ["data engineer", "etl", "pipeline", "spark", "airflow", "warehouse", "bigquery", "hive", "data lake"],
        "ML": ["machine learning", "ml", "deep learning", "ai", "model", "pytorch", "tensorflow", "nlp", "computer vision"],
    }

    for profile, keywords in kw_map.items():
        for kw in keywords:
            if kw in text_lower:
                scores[profile] += 1

    return max(scores, key=scores.get)


def _select_projects(projects, jd_keywords, max_items=3):
    """Select projects most relevant to the JD."""
    scored = []
    for proj in projects:
        tags = set(proj.get("tags", []))
        score = len(tags & jd_keywords)
        # Also check project tech stack
        tech_lower = proj.get("tech", "").lower()
        score += sum(1 for kw in jd_keywords if kw in tech_lower)
        scored.append((score, proj))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_items]]


# ==============================
# LATEX GENERATION
# ==============================

def _generate_latex(job, profile_name, jd_keywords):
    """Generate ATS-optimized LaTeX document matching the candidate's existing format."""
    data = RESUME_DATA
    job_title = str(job.get("job_title", "Software Engineer"))

    summary = _build_ats_summary(job_title, jd_keywords, profile_name)
    skills = _build_ats_skills_section(jd_keywords)

    experience_sections = []
    for exp in data["experience"]:
        # Primary role gets more bullets, internship gets fewer
        is_primary = exp.get("end", "") == "Present" or exp == data["experience"][0]
        max_b = 10 if is_primary else 7
        bullets = _select_ats_bullets(exp["bullets"], exp.get("tags", []), jd_keywords, max_bullets=max_b)
        experience_sections.append({**exp, "bullets": bullets})

    projects = _select_projects(data["projects"], jd_keywords, max_items=3)

    # Preamble matching existing resume format
    latex = r"""\documentclass[a4paper,10pt]{article}

\usepackage[left=0.6in,right=0.6in,top=0.6in,bottom=0.6in]{geometry}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{titlesec}
\usepackage{multicol}
\usepackage{xcolor}

\setlength{\parindent}{0pt}
\setlist[itemize]{leftmargin=*, itemsep=2pt, topsep=2pt}

\titleformat{\section}
{\large\bfseries}
{}
{0em}
{}[\titlerule]

\begin{document}

\begin{center}
    {\LARGE \textbf{""" + _escape_latex(data["name"]) + r"""}}\\[4pt]
    """ + _escape_latex(data["phone"]) + r""" \;|\;
    \href{mailto:""" + data["email"] + r"""}{""" + _escape_latex(data["email"]) + r"""} \;|\;
    \href{""" + data["linkedin"] + r"""}{LinkedIn} \;|\;
    \href{""" + data["github"] + r"""}{GitHub}
\end{center}

%------------------------------------------------

\section*{Summary}

""" + _escape_latex(summary) + r"""

%------------------------------------------------

\section*{Education}

"""

    # Education
    for edu in data["education"]:
        latex += r"\textbf{" + _escape_latex(edu["institution"]) + r"}, " + _escape_latex(edu["location"]) + r"\\" + "\n"
        latex += _escape_latex(edu["degree"]) + r" \hfill " + _escape_latex(edu["year"]) + r"\\" + "\n"
        if edu.get("gpa"):
            latex += "CGPA: " + edu["gpa"] + "\n"
        latex += "\n"

    # Experience
    latex += r"""%------------------------------------------------

\section*{Experience}

"""

    for i, exp in enumerate(experience_sections):
        latex += r"\textbf{" + _escape_latex(exp["company"]) + r"} \hfill " + _escape_latex(exp["start"]) + " -- " + _escape_latex(exp["end"]) + r"\\" + "\n"
        latex += r"\textit{" + _escape_latex(exp["title"]) + r"}" + "\n\n"
        latex += r"\begin{itemize}" + "\n"
        for bullet in exp["bullets"]:
            latex += r"    \item " + _escape_latex(bullet) + "\n"
        latex += r"\end{itemize}" + "\n"
        if i < len(experience_sections) - 1:
            latex += "\n" + r"\vspace{4pt}" + "\n\n"

    # Projects
    latex += r"""
%------------------------------------------------

\section*{Projects}

"""

    for i, proj in enumerate(projects):
        bullets = _select_ats_bullets(proj["bullets"], proj.get("tags", []), jd_keywords, max_bullets=8)
        latex += r"\textbf{" + _escape_latex(proj["name"]) + r"}\\" + "\n"
        latex += r"\textit{" + _escape_latex(proj["tech"]) + r"}" + "\n\n"
        latex += r"\begin{itemize}" + "\n"
        for bullet in bullets:
            latex += r"    \item " + _escape_latex(bullet) + "\n"
        latex += r"\end{itemize}" + "\n"
        if i < len(projects) - 1:
            latex += "\n" + r"\vspace{4pt}" + "\n\n"

    # Technical Skills
    latex += r"""
%------------------------------------------------

\section*{Technical Skills}

"""

    category_labels = {
        "languages": "Programming Languages",
        "frameworks": "Frameworks \\& Libraries",
        "databases": "Databases \\& Data Warehousing",
        "cloud_devops": "Cloud \\& DevOps",
        "data_ml": "Data Science \\& Analytics",
        "tools": "Core Concepts",
    }

    skill_entries = list(skills.items())
    for i, (category, skill_list) in enumerate(skill_entries):
        label = category_labels.get(category, category.replace("_", " ").title())
        latex += r"\textbf{" + label + r":}" + "\n"
        latex += ", ".join(_escape_latex(s) for s in skill_list) + "\n"
        if i < len(skill_entries) - 1:
            latex += "\n" + r"\vspace{4pt}" + "\n\n"

    latex += r"""
\end{document}
"""
    return latex


# ==============================
# PUBLIC API
# ==============================

def generate_resume(job):
    """
    Generate an ATS-optimized job-specific LaTeX resume.

    The resume is tailored to maximize ATS keyword matching:
    - Summary mirrors the job title and top JD keywords
    - Skills section only shows what the JD asks for
    - Experience bullets are selected by JD keyword density
    - Projects are picked by relevance to JD requirements
    - Single-column, no-graphics format for ATS parseability

    Args:
        job: dict with job_title, company_name, job_description, job_url

    Returns:
        dict with pdf_path, tex_path, profile, matched_skills on success
    """
    _ensure_output_dir()

    job_text = str(job.get("job_description", "")) + " " + str(job.get("job_title", ""))
    jd_keywords = _extract_jd_keywords(job_text)
    profile_name = _pick_profile(job_text)

    # Generate ATS-optimized LaTeX
    latex_content = _generate_latex(job, profile_name, jd_keywords)

    # File naming
    company = re.sub(r"[^a-zA-Z0-9]", "_", str(job.get("company_name", job.get("company", "unknown"))))[:20]
    title = re.sub(r"[^a-zA-Z0-9]", "_", str(job.get("job_title", "job")))[:30]
    short_hash = hashlib.md5(str(job.get("job_url", job_text[:100])).encode()).hexdigest()[:6]
    filename = f"{company}_{title}_{short_hash}"

    tex_path = OUTPUT_DIR / f"{filename}.tex"
    pdf_path = OUTPUT_DIR / f"{filename}.pdf"

    # Write .tex
    tex_path.write_text(latex_content, encoding="utf-8")

    # Compile to PDF
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(OUTPUT_DIR), str(tex_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if pdf_path.exists():
            # Clean aux files
            for ext in [".aux", ".log", ".out"]:
                aux = OUTPUT_DIR / f"{filename}{ext}"
                if aux.exists():
                    aux.unlink()

            return {
                "pdf_path": str(pdf_path),
                "tex_path": str(tex_path),
                "profile": profile_name,
                "matched_skills": sorted(jd_keywords),
            }
        else:
            return {
                "error": "pdflatex compilation failed. Check the .tex file manually.",
                "tex_path": str(tex_path),
                "profile": profile_name,
                "matched_skills": sorted(jd_keywords),
            }
    except FileNotFoundError:
        return {
            "error": "pdflatex not found. Install MiKTeX or TeX Live.",
            "tex_path": str(tex_path),
            "profile": profile_name,
            "matched_skills": sorted(jd_keywords),
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "pdflatex timed out.",
            "tex_path": str(tex_path),
            "profile": profile_name,
            "matched_skills": sorted(jd_keywords),
        }
