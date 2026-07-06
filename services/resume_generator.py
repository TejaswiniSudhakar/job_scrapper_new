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
        # Check if candidate actually has this skill
        all_candidate_skills = set()
        for skills in data["skills"].values():
            all_candidate_skills.update(s.lower() for s in skills)
        for exp in data["experience"]:
            all_candidate_skills.update(t.lower() for t in exp.get("tags", []))
        if kw in all_candidate_skills:
            priority_skills.append(kw)

    # Cap at 8 most important skills for the summary
    priority_skills = priority_skills[:8]

    # Build summary with job title and matched keywords
    skill_str = ", ".join(s.title() if len(s) > 3 else s.upper() for s in priority_skills[:6])

    summary = (
        f"{title_clean} with {CANDIDATE_YEARS} years of hands-on experience. "
        f"Proficient in {skill_str}. "
    )

    # Add profile-specific closer
    closers = {
        "Backend": "Experienced in building scalable backend services, REST APIs, and distributed systems.",
        "cloud_engineer": "Experienced in cloud infrastructure, containerization, and CI/CD automation.",
        "data_engineer": "Experienced in building data pipelines, ETL workflows, and large-scale data processing.",
        "ML": "Experienced in building and deploying machine learning models in production environments.",
    }
    summary += closers.get(profile_name, closers["Backend"])

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
    """Generate ATS-optimized LaTeX document.
    - Single column (ATS-friendly)
    - No graphics or tables
    - Keywords from JD woven throughout
    - Clean section headers ATS can parse
    """
    data = RESUME_DATA
    job_title = str(job.get("job_title", "Software Engineer"))

    # ATS-optimized summary with job title and JD keywords
    summary = _build_ats_summary(job_title, jd_keywords, profile_name)

    # Only skills from the JD
    skills = _build_ats_skills_section(jd_keywords)

    # Experience bullets selected by JD keyword density
    experience_sections = []
    for exp in data["experience"]:
        bullets = _select_ats_bullets(exp["bullets"], exp.get("tags", []), jd_keywords, max_bullets=5)
        experience_sections.append({**exp, "bullets": bullets})

    # Projects most relevant to JD
    projects = _select_projects(data["projects"], jd_keywords, max_items=2)

    # Build LaTeX - clean ATS-parseable format
    latex = r"""\documentclass[11pt,a4paper]{article}

\usepackage[margin=0.55in]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\usepackage[T1]{fontenc}
\usepackage{lmodern}

\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}

\titleformat{\section}{\large\bfseries\uppercase}{}{0em}{}[\titlerule]
\titlespacing*{\section}{0pt}{8pt}{5pt}

\setlist[itemize]{nosep, leftmargin=16pt, label=\textbullet, topsep=2pt}

\begin{document}

% ===== HEADER =====
\begin{center}
    {\LARGE\bfseries """ + _escape_latex(data["name"]) + r"""}\\[3pt]
    """ + _escape_latex(data["location"]) + r""" \quad $\vert$ \quad """ + _escape_latex(data["phone"]) + r""" \quad $\vert$ \quad """ + _escape_latex(data["email"]) + r"""\\[2pt]
    \href{https://""" + data["linkedin"] + r"""}{""" + _escape_latex(data["linkedin"]) + r"""} \quad $\vert$ \quad \href{https://""" + data["github"] + r"""}{""" + _escape_latex(data["github"]) + r"""}
\end{center}

% ===== SUMMARY =====
\section{Summary}
""" + _escape_latex(summary) + r"""

% ===== SKILLS (JD-matched only) =====
\section{Technical Skills}
\begin{itemize}[leftmargin=0pt, label={}]
"""

    category_labels = {
        "languages": "Languages",
        "frameworks": "Frameworks \\& Libraries",
        "databases": "Databases",
        "cloud_devops": "Cloud \\& DevOps",
        "data_ml": "Data \\& ML",
        "tools": "Tools \\& Practices",
    }
    for category, skill_list in skills.items():
        label = category_labels.get(category, category.replace("_", " ").title())
        latex += r"    \item \textbf{" + label + r":} " + ", ".join(skill_list) + "\n"

    latex += r"""\end{itemize}

% ===== EXPERIENCE =====
\section{Experience}
"""

    for exp in experience_sections:
        latex += r"\textbf{" + _escape_latex(exp["title"]) + r"} \hfill " + _escape_latex(exp["start"]) + " -- " + _escape_latex(exp["end"]) + r"\\" + "\n"
        latex += r"\textit{" + _escape_latex(exp["company"]) + r"} \hfill " + _escape_latex(exp["location"]) + r"\\" + "\n"
        latex += r"\begin{itemize}" + "\n"
        for bullet in exp["bullets"]:
            latex += r"    \item " + bullet + "\n"
        latex += r"\end{itemize}" + "\n"
        latex += r"\vspace{3pt}" + "\n"

    # ===== PROJECTS =====
    latex += r"""
% ===== PROJECTS =====
\section{Projects}
"""
    for proj in projects:
        bullets = _select_ats_bullets(proj["bullets"], proj.get("tags", []), jd_keywords, max_bullets=2)
        latex += r"\textbf{" + _escape_latex(proj["name"]) + r"} $\vert$ \textit{" + _escape_latex(proj["tech"]) + r"}\\" + "\n"
        latex += r"\begin{itemize}" + "\n"
        for bullet in bullets:
            latex += r"    \item " + _escape_latex(bullet) + "\n"
        latex += r"\end{itemize}" + "\n"
        latex += r"\vspace{3pt}" + "\n"

    # ===== EDUCATION =====
    latex += r"""
% ===== EDUCATION =====
\section{Education}
"""
    for edu in data["education"]:
        latex += r"\textbf{" + _escape_latex(edu["degree"]) + r"} \hfill " + _escape_latex(edu["year"]) + r"\\" + "\n"
        latex += r"\textit{" + _escape_latex(edu["institution"]) + r"} \hfill " + _escape_latex(edu["location"])
        if edu.get("gpa"):
            latex += r" \quad GPA: " + edu["gpa"]
        latex += "\n"

    # ===== CERTIFICATIONS =====
    if data.get("certifications"):
        latex += r"""
% ===== CERTIFICATIONS =====
\section{Certifications}
\begin{itemize}
"""
        for cert in data["certifications"]:
            latex += r"    \item " + _escape_latex(cert["name"]) + " (" + cert["year"] + ")\n"
        latex += r"\end{itemize}" + "\n"

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
