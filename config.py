from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


APP_CONFIG = {
    "files": {
        "jobs_db": BASE_DIR / "jobs.db",
        "seen_jobs_db": BASE_DIR / "data" / "seen_jobs.db",
        "jobs_csv": BASE_DIR / "jobs.csv",
        "log_file": BASE_DIR / "log.txt",
        "resumes_dir": BASE_DIR / "scrapers" / "resumes",
        "generated_resumes_dir": BASE_DIR / "generated_resumes",
    },
    "candidate": {
        "name": "Your Name",
        "email": "your.email@example.com",
        "phone": "your-phone-number",
        "address": "Your address",
        "experience_years": 1.3,
        "resume_summary": (
            "Java Backend Developer skilled in Java, Spring Boot, Microservices architecture, "
            "REST API development, Oracle SQL, and advanced PL/SQL. Experience building enterprise "
            "applications using Apache Tomcat, working with relational databases, writing stored "
            "procedures, and optimizing queries. Familiar with full-stack development concepts, Git "
            "version control, Agile development practices, and automated testing using DevPlus. "
            "Interested in backend, microservices, cloud, and full-stack engineering roles. "
            "Experience with web scraping automation, Python scripting, Selenium, and building tools "
            "for job aggregation and automation. Job experience 1.3 years"
        ),
        "key_skills": [
            "java",
            "spring",
            "spring boot",
            "microservices",
            "rest",
            "gcp",
            "ci/cd",
            "docker",
            "kubernetes",
            "sql",
            "oracle",
            "pl/sql",
        ],
    },
    "ranking": {
        "threshold": 8,
        "expected_min_salary": 1_000_000,
        "expected_max_salary": 3_000_000,
    },
    "scrapers": {
        "keywords": [
            "Software Engineer",
            "Java Developer",
            "Backend Developer",
            "Spring Boot Developer",
            "Microservices Developer",
            "Cloud Engineer",
            "Google Cloud Engineer",
            "SQL Developer",
            "PL/SQL Developer",
            "Data Engineer",
            "Python Developer",
            "Backend Python Developer",
            "Full Stack Developer",
            "API Developer",
            "Platform Engineer",
            "Systems Engineer",
            "Full Stack Engineer",
            "Junior Software Engineer",
            "Associate Software Engineer",
            "Fresher Software Engineer",
        ],
        "indeed": {
            "location": "Bengaluru, Karnataka",
            "radius": 35,
            "days_old": 1,
            "use_logged_in_profile": True,
            "chrome_profile_dir": str(Path.home() / "my_scraper" / "selenium_profile_indeed1"),
            "chrome_profile_name": "Default",
        },
        "linkedin": {
            "locations": ["Bangalore"],
            "date_posted": "24h",
            "max_scrolls": 50,
        },
        "naukri": {
            "location": "bengaluru",
            "experience": "2",
            "use_logged_in_profile": True,
            "chrome_profile_dir": str(Path.home() / "my_scraper" / "selenium_profile"),
        },
        # --- v2 scrapers: logged-in versions with updated selectors.
        # Separate chrome_profile_dir so they can run alongside the v1
        # scrapers without fighting over the same Chrome user-data-dir. ---
        "linkedin_v2": {
            "locations": ["Bangalore"],
            "date_posted": "24h",
            # Experience levels: 1 = Internship, 2 = Entry Level, 3 = Associate
            "experience_levels": "1,2,3",
            "use_logged_in_profile": True,
            "chrome_profile_dir": str(Path.home() / "my_scraper" / "selenium_profile_linkedin_v2"),
        },
        "naukri_v2": {
            "location": "bengaluru",
            "experience": "2",
            "job_age": 1,
            "use_logged_in_profile": True,
            "chrome_profile_dir": str(Path.home() / "my_scraper" / "selenium_profile_naukri_v2"),
        },
        "indeed_v2": {
            "location": "Bengaluru, Karnataka",
            "radius": 35,
            "days_old": 1,
            "use_logged_in_profile": True,
            "chrome_profile_dir": str(Path.home() / "my_scraper" / "selenium_profile_indeed_v2"),
            "chrome_profile_name": "Default",
        },
    },
    "queue": {
        "max_size": 500,
    },
    "export": {
        "interval_seconds": 60,
    },
}