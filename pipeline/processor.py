import sys
import os
from config import APP_CONFIG

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.deduplicator import is_seen, mark_seen, get_job_id
from services.ranker import rank_job
from services.cover_letter import generate_cover_letter_for_job
from services.notifier import send_email
from services.storage import save_job
from services.job_fields import normalize_job_fields
from services.logging_utils import get_logger
from queue_manager import job_queue

THRESHOLD = APP_CONFIG["ranking"]["threshold"]
COVER_LETTER_MIN_SCORE = APP_CONFIG["ranking"].get("cover_letter_min_score", 7)
logger = get_logger("processor")


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

            job = normalize_job_fields(job)

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
            if final_score >= COVER_LETTER_MIN_SCORE:
                job["cover_letter"] = generate_cover_letter_for_job(job)
                # ---- Notify ----
                send_email(job)
            else:
                job["cover_letter"] = "Skipped: final score below 7 to save Gemini tokens."
                logger.info(
                    "Cover letter skipped | title=%s | final_score=%.2f | min_score=%.2f",
                    job["job_title"],
                    final_score,
                    COVER_LETTER_MIN_SCORE,
                )

            save_job(job, final_score)

            # ---- Mark only after success ----
            mark_seen(job_id)

        except Exception as e:
            logger.exception("Processor error: %s", e)

        finally:
            job_queue.task_done()
