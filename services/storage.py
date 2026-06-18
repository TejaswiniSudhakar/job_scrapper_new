import sqlite3
import hashlib
import threading
from datetime import datetime
from config import APP_CONFIG

# ==============================
# CONFIG
# ==============================
DB_NAME = str(APP_CONFIG["files"]["jobs_db"])

# Thread lock for safe writes
lock = threading.Lock()


# ==============================
# INIT DB
# ==============================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        conn.commit()
        # Create table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash TEXT UNIQUE,
            job_url TEXT,
            source TEXT,
            company TEXT,
            title TEXT,
            experience_required TEXT,
            salary TEXT,
            location TEXT,
            job_description TEXT,
            final_score REAL,
            pre_score REAL,
            gpt_score REAL,
            reason TEXT,
            cover_letter TEXT,
            created_at TIMESTAMP
        )
        """)

        conn.commit()


        ensure_column(cursor, "salary", "TEXT")
        ensure_column(cursor, "location", "TEXT")

        conn.commit()


def ensure_column(cursor, column_name, column_type):
    cursor.execute("PRAGMA table_info(jobs)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")


# ==============================
# HASH FUNCTION
# ==============================
def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


# ==============================
# CHECK IF JOB EXISTS
# ==============================
def job_exists(job_url):

    url_hash = hash_url(job_url)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM jobs WHERE url_hash = ?",
            (url_hash,)
        )

        return cursor.fetchone() is not None


# ==============================
# SAVE JOB
# ==============================
def save_job(job, score):

    url = job.get("job_url")
    if not url:
        return

    url_hash = hash_url(url)

    with lock:
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                INSERT INTO jobs (
                    url_hash,
                    job_url,
                    source,
                    company,
                    title,
                    experience_required,
                    salary,
                    location,
                    job_description,
                    final_score,
                    pre_score,
                    gpt_score,
                    reason,
                    cover_letter,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    url_hash,
                    url,
                    job.get("source"),
                    job.get("company_name"),
                    job.get("job_title"),
                    job.get("experience_required", "Not mentioned"),
                    job.get("salary", "Not mentioned"),
                    job.get("location", ""),
                    job.get("job_description", "")[:4000],  # Truncate to fit in DB
                    job.get("final_score"),
                    job.get("pre_score"),
                    job.get("gpt_score"),
                    job.get("reason", "No reason provided"),
                    job.get("cover_letter"),
                    datetime.now()
                ))

                conn.commit()
                print("✅ Job saved successfully")

        except sqlite3.IntegrityError:
            # Duplicate (already exists)
            pass


# ==============================
# OPTIONAL: CLEAN OLD JOBS
# ==============================
def cleanup_old_jobs(days=7):

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        DELETE FROM jobs
        WHERE created_at < datetime('now', ?)
        """, (f"-{days} days",))

        conn.commit()
