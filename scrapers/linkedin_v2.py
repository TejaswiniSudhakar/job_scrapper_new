import random
import re
import time
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import APP_CONFIG
from pipeline.deduplicator import hash_job_url, is_passed, mark_passed
from queue_manager import enqueue_job
from scrapers.common import get_experience_from_description
from services.driver_registry import register_driver
from services.logging_utils import get_logger, log_cycle_summary, log_iteration_summary
from services.storage import job_exists


logger = get_logger("scraper.linkedin_v2")
SCRAPER_CONFIG = APP_CONFIG["scrapers"]
LINKEDIN_V2_CONFIG = SCRAPER_CONFIG["linkedin_v2"]
SOURCE_LABEL = "LinkedIn v2"

JOB_KEYWORDS = SCRAPER_CONFIG["keywords"]
COUNTRIES = LINKEDIN_V2_CONFIG["locations"]
PROFILE_DIR = LINKEDIN_V2_CONFIG["chrome_profile_dir"]
EXPERIENCE_LEVELS = LINKEDIN_V2_CONFIG.get("experience_levels", "1,2,3")

# --- Pacing ---
# LinkedIn has been warning about request volume, so every wait here is
# intentionally generous. Tune these via config.py under
# scrapers.linkedin_v2 (keys below) if you want to override without
# editing code - defaults are deliberately slow.
PAGE_LOAD_PAUSE = LINKEDIN_V2_CONFIG.get("page_load_pause", (20, 40))
JOB_VISIT_PAUSE = LINKEDIN_V2_CONFIG.get("job_visit_pause", (10, 20))
TARGET_BREAK_PAUSE = LINKEDIN_V2_CONFIG.get("target_break_pause", (60, 120))
CYCLE_BREAK_PAUSE = LINKEDIN_V2_CONFIG.get("cycle_break_pause", (1200, 2400))  # 20-40 min
KEYWORDS_PER_BATCH = LINKEDIN_V2_CONFIG.get("keywords_per_batch", 2)
BATCH_BREAK_PAUSE = LINKEDIN_V2_CONFIG.get("batch_break_pause", (300, 600))  # 5-10 min

# Extra searches defined by LinkedIn geoId (instead of a free-text location),
# each optionally with its own experience-level filter. Add more entries in
# config.py under scrapers.linkedin_v2.geo_targets to scrape additional
# geoId-based searches, e.g. ones copied straight from a LinkedIn search URL.
GEO_TARGETS = LINKEDIN_V2_CONFIG.get(
    "geo_targets",
    [
        {
            "label": "geoId:105214831 (entry/associate)",
            "geo_id": "105214831",
            "experience_levels": "2,3",
        }
    ],
)

# Unified list of search targets: each is either location-text based or
# geoId based. Both feed into build_linkedin_url() below.
SEARCH_TARGETS = [
    {"label": loc, "location": loc, "experience_levels": None} for loc in COUNTRIES
] + [
    {
        "label": gt.get("label", f"geoId:{gt['geo_id']}"),
        "geo_id": gt["geo_id"],
        "experience_levels": gt.get("experience_levels"),
    }
    for gt in GEO_TARGETS
]


def random_pause(bounds):
    """bounds is a (min_seconds, max_seconds) tuple."""
    time.sleep(random.uniform(*bounds))


def create_driver():
    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)


def is_logged_in(driver):
    """Check whether LinkedIn session is active."""
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(3)

    current_url = driver.current_url.lower()
    if "login" in current_url:
        return False
    if "checkpoint" in current_url:
        return False
    return True


def wait_for_manual_login(driver, timeout=600):
    """Wait up to 10 minutes for manual login."""
    start = time.time()

    while time.time() - start < timeout:
        current_url = driver.current_url.lower()

        if "/feed" in current_url or "/jobs" in current_url or "/mynetwork" in current_url:
            logger.info("LinkedIn (v2) login successful.")
            return True

        time.sleep(3)

    return False


def ensure_login(driver):
    if is_logged_in(driver):
        logger.info("LinkedIn (v2) already logged in.")
        return True

    logger.info("LinkedIn (v2) login required.")
    driver.get("https://www.linkedin.com/login")
    logger.info("Waiting for manual LinkedIn login...")

    return wait_for_manual_login(driver)


def build_linkedin_url(keyword, location=None, geo_id=None, experience_levels=None):
    params = [f"keywords={quote_plus(keyword)}"]

    if geo_id:
        params.append(f"geoId={quote_plus(str(geo_id))}")
    elif location:
        params.append(f"location={quote_plus(location)}")

    params.append(f"f_E={quote_plus(experience_levels or EXPERIENCE_LEVELS)}")
    # Last 24 hours
    params.append("f_TPR=r86400")
    # Sort by newest
    params.append("sortBy=DD")

    return "https://www.linkedin.com/jobs/search/?" + "&".join(params)


def get_total_jobs(driver):
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-search-results-list__subtitle span"))
        )

        text = element.text.strip()
        match = re.search(r"(\d[\d,]*)", text)

        if match:
            return int(match.group(1).replace(",", ""))

        return 0
    except Exception:
        logger.warning("LinkedIn (v2) job count not available for current page.")
        return 0



def wait_for_card_content(card, timeout=3):
    """Block until this specific card's inner content has mounted."""
    def _loaded(_):
        try:
            card.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__title")
            return True
        except Exception:
            return False

    try:
        WebDriverWait(card.parent, timeout).until(_loaded)
        return True
    except Exception:
        return False


def scrape_card(card):
    """Scroll a card into view, wait for it to render, then extract its fields."""
    card.parent.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)

    if not wait_for_card_content(card):
        return None

    try:
        link_elem = card.find_element(By.CSS_SELECTOR, "a.job-card-container__link")
        title = link_elem.text.strip()
        job_link = link_elem.get_attribute("href").split("?")[0]
    except Exception:
        title, job_link = None, None

    try:
        company = card.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__subtitle").text.strip()
    except Exception:
        company = None

    try:
        job_location = card.find_element(
            By.CSS_SELECTOR, ".artdeco-entity-lockup__caption span[dir='ltr']"
        ).text.strip()
    except Exception:
        job_location = None

    return {
        "title": title,
        "company": company,
        "link": job_link,
        "location": job_location,
    }


def fetch_job_description(driver, job_url, timeout=10):
    """Visit a job's own page and pull the full description text."""
    driver.get(job_url)

    selector = "#job-details, [data-testid='expandable-text-box']"

    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    except Exception:
        logger.warning("LinkedIn (v2) could not load description for %s", job_url)
        return ""

    try:
        see_more_btn = driver.find_element(
            By.XPATH,
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'see more') or "
            "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
        )
        driver.execute_script("arguments[0].click();", see_more_btn)
        time.sleep(2)
    except Exception:
        pass

    try:
        desc_elem = driver.find_element(By.CSS_SELECTOR, selector)
        return desc_elem.text.strip()
    except Exception:
        logger.warning("LinkedIn (v2) could not read description for %s", job_url)
        return ""


def linkedin_v2():
    """
    Logged-in LinkedIn scraper with updated DOM selectors, wired into the
    same pipeline (queue, dedup, storage, logging) as the original
    linkedIn() in linkedIn_old.py. Run both side-by-side; they use separate
    Chrome profiles so they won't conflict.

    Pacing is intentionally slow throughout (see the constants near the
    top of this file) - LinkedIn started warning about request volume,
    so every wait here errs heavily toward "too slow" over "too fast".
    """
    driver = create_driver()
    register_driver(driver)

    try:
        if not ensure_login(driver):
            logger.warning("LinkedIn (v2) login timeout. Stopping.")
            return

        seen_urls = set()  # persists across every cycle for the life of this run

        while True:
            total_jobs_found = 0
            fresh_jobs = 0
            cycle_start = time.time()

            try:
                for keyword_index, keyword in enumerate(JOB_KEYWORDS, start=1):
                    for target in SEARCH_TARGETS:
                        label = target["label"]
                        iteration_start = time.time()
                        iteration_jobs_found = 0
                        iteration_fresh_jobs = 0

                        base_url = build_linkedin_url(
                            keyword,
                            location=target.get("location"),
                            geo_id=target.get("geo_id"),
                            experience_levels=target.get("experience_levels"),
                        )
                        driver.get(base_url)
                        random_pause(PAGE_LOAD_PAUSE)

                        expected_jobs = get_total_jobs(driver)
                        logger.info("Found %s jobs for '%s' in '%s'", expected_jobs, keyword, label)

                        for start in range(0, expected_jobs, 25):
                            page_url = f"{base_url}&start={start}"

                            driver.get(page_url)
                            random_pause(PAGE_LOAD_PAUSE)

                            job_cards = driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")

                            page_jobs = []
                            for card in job_cards:
                                try:
                                    job = scrape_card(card)
                                    if job is None:
                                        continue
                                    page_jobs.append(job)
                                except Exception:
                                    logger.exception(
                                        "LinkedIn (v2) card parsing failed | keyword=%s | location=%s",
                                        keyword,
                                        label,
                                    )

                            iteration_jobs_found += len(page_jobs)
                            total_jobs_found += len(page_jobs)

                            # --- visit each new job's own page for the full description ---
                            for job in page_jobs:
                                try:
                                    job_url = job["link"]
                                    if not job_url or job_url in seen_urls:
                                        continue

                                    url_hash = hash_job_url(job_url)
                                    if is_passed(url_hash) or job_exists(job_url):
                                        continue

                                    seen_urls.add(job_url)
                                    mark_passed(url_hash)

                                    job_description = fetch_job_description(driver, job_url)
                                    experience = get_experience_from_description(
                                        job_description + (job["title"] or "")
                                    )

                                    job_data = {
                                        "job_url": job_url,
                                        "job_title": job["title"],
                                        "company_name": job["company"],
                                        "location": job["location"],
                                        "job_description": job_description,
                                        "experience_required": experience,
                                        "source": SOURCE_LABEL,
                                    }

                                    if enqueue_job(job_data):
                                        iteration_fresh_jobs += 1
                                        fresh_jobs += 1

                                    logger.info("LinkedIn (v2) queued: %s", job["title"])
                                except Exception:
                                    logger.exception("LinkedIn (v2) failed to process job: %s", job.get("link"))

                                random_pause(JOB_VISIT_PAUSE)

                        log_iteration_summary(
                            logger,
                            "LinkedIn-v2",
                            f"keyword='{keyword}' location='{label}'",
                            iteration_jobs_found,
                            iteration_fresh_jobs,
                            time.time() - iteration_start,
                        )

                        # Pause between different search targets (locations / geoIds)
                        # for the same keyword - this is a separate full search
                        # results page load from LinkedIn's point of view.
                        random_pause(TARGET_BREAK_PAUSE)

                    # Longer break every couple of keywords, on top of the
                    # existing per-page/per-job pauses, to cap burst traffic.
                    if keyword_index % KEYWORDS_PER_BATCH == 0 and keyword_index != len(JOB_KEYWORDS):
                        logger.info("LinkedIn (v2) batch break after %s keywords.", keyword_index)
                        random_pause(BATCH_BREAK_PAUSE)

                # Long pause between full keyword/location sweeps before
                # starting the next cycle.
                logger.info("LinkedIn (v2) cycle complete. Taking a long break before next cycle.")
                random_pause(CYCLE_BREAK_PAUSE)

            except Exception:
                logger.exception("LinkedIn (v2) fatal cycle error. Recreating driver.")
                try:
                    driver.quit()
                except Exception:
                    pass

                random_pause((30, 60))
                driver = create_driver()
                if not ensure_login(driver):
                    logger.warning("LinkedIn (v2) login timeout after driver recreation. Stopping.")
                    break

            finally:
                log_cycle_summary(
                    logger,
                    "LinkedIn-v2",
                    total_jobs_found,
                    fresh_jobs,
                    time.time() - cycle_start,
                )

    except KeyboardInterrupt:
        logger.info("LinkedIn (v2) shutting down.")

    finally:
        driver.quit()


if __name__ == "__main__":
    linkedin_v2()