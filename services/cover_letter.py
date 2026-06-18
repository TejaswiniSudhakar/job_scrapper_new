from openai import OpenAI
from config import APP_CONFIG
from dotenv import load_dotenv
import os
from services.logging_utils import get_logger

# ==============================
# LOAD ENV
# ==============================
load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# CANDIDATE = APP_CONFIG["candidate"]
# logger = get_logger("cover_letter")


# ==============================
# MAIN FUNCTION (UNCHANGED STYLE)
# ==============================
def generate_letter(job_title, company_name, job_description):

    prompt = f"""
Write a concise professional cover letter.

Job Title: {job_title}
Company: {company_name}

Job Description:
{job_description[:2000]}

Candidate profile:
{CANDIDATE["resume_summary"]}

Candidate Details:
Phone: {CANDIDATE["phone"]}
Email: {CANDIDATE["email"]}
Address: {CANDIDATE["address"]}

Requirements:
- 150 words
- Professional tone
- Mention relevant backend engineering skills
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    return response.choices[0].message.content.strip()


# ==============================
# NEW: STREAMING VERSION
# ==============================
# def generate_cover_letter_for_job(job):

#     try:
#         return generate_letter(
#             job.get("job_title", ""),
#             job.get("company_name", ""),
#             job.get("job_description", "")
#         )
#     except Exception as e:
#         logger.exception("Cover letter failed: %s", e)
#         return ""
