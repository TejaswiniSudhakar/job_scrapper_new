import sys
import os
import re
from config import APP_CONFIG

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.deduplicator import is_seen, mark_seen, get_job_id
from services.ranker import rank_job
from services.notifier import send_email
from services.storage import save_job
from services.logging_utils import get_logger
from queue_manager import job_queue

THRESHOLD = APP_CONFIG["ranking"]["threshold"]
MAX_EXPERIENCE_YEARS = 3
logger = get_logger("processor")

# Job title must contain at least one of these to be considered IT-relevant
IT_TITLE_KEYWORDS = [
    "software", "developer", "engineer", "programming", "programmer",
    "backend", "frontend", "fullstack", "full stack", "full-stack",
    "devops", "sre", "cloud", "platform", "infrastructure",
    "data engineer", "data scientist", "data analyst", "machine learning", "ml ",
    "ai ", "artificial intelligence", "deep learning", "nlp",
    "java", "python", "golang", "node", "react", "angular",
    "microservices", "api", "web developer",
    "database", "dba", "sql", "etl",
    "qa", "sdet", "test automation", "quality",
    "security", "cybersecurity", "infosec",
    "architect", "technical lead", "tech lead",
    "systems", "network", "linux", "unix",
    "mobile", "android", "ios", "flutter",
    "blockchain", "embedded", "firmware",
    "it ", "information technology",
]


def _exceeds_max_experience(exp_text):
    """Return True if the job requires more than MAX_EXPERIENCE_YEARS."""
    numbers = re.findall(r"\d+", str(exp_text))
    if not numbers:
        return False
    # Use the minimum number in the range as the requirement
    required = min(int(n) for n in numbers if 0 <= int(n) <= 25)
    return required > MAX_EXPERIENCE_YEARS if numbers else False


def processor():
  
    # clear_seen_jobs()
    logger.info("Processor started.")

    while True:
        job = job_queue.get()

        try:
            job_id = get_job_id(job["job_title"], job["company_name"], job["job_description"]   )

            # ---- Deduplication ----
            if is_seen(job_id):
                logger.info("Duplicate skipped: %s", job["job_title"])
                continue

            # ---- Title relevance filter (IT roles only) ----
            title_lower = job.get("job_title", "").lower()
            if not any(kw in title_lower for kw in IT_TITLE_KEYWORDS):
                mark_seen(job_id)
                logger.info("Skipped (non-IT title): %s", job["job_title"])
                continue

            # ---- Experience filter ----
            exp_text = job.get("experience_required", "")
            if _exceeds_max_experience(exp_text):
                mark_seen(job_id)
                logger.info("Skipped (>%d yrs required): %s", MAX_EXPERIENCE_YEARS, job["job_title"])
                continue

            # ---- Ranking ----
            pre_score, gpt_score, final_score, reason = rank_job(job)
            job["pre_score"] = pre_score
            job["gpt_score"] = gpt_score
            job["final_score"] = final_score
            job["reason"] = reason
            logger.info(
                "Ranked job | title=%s | pre_score=%.2f | gpt_score=%.2f | final_score=%.2f",
                job["job_title"],
                pre_score,
                gpt_score,
                final_score,
            )
            # ---- Filter low quality ----
            if final_score < THRESHOLD:
                mark_seen(job_id)  # safe to mark now
                save_job(job, final_score)

                continue

            # ---- Cover letter ----
            # job["cover_letter"] = generate_cover_letter_for_job(job)
            # save_job(job, final_score)
            # # ---- Notify ----
            # send_email(job)

            # ---- Mark only after success ----
            mark_seen(job_id)

        except Exception as e:
            logger.exception("Processor error: %s", e)

        finally:
            job_queue.task_done()
