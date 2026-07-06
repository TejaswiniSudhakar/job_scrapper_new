import random
import re
import time
from math import ceil

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import APP_CONFIG
from pipeline.deduplicator import get_job_id, hash_job_url, is_passed, mark_passed
from queue_manager import enqueue_job
from services.driver_registry import register_driver
from services.logging_utils import get_logger, log_cycle_summary, log_iteration_summary
from services.storage import job_exists


logger = get_logger("scraper.naukri_v2")
SCRAPER_CONFIG = APP_CONFIG["scrapers"]
NAUKRI_V2_CONFIG = SCRAPER_CONFIG["naukri_v2"]
SOURCE_LABEL = "Naukri v2"

JOB_KEYWORDS = SCRAPER_CONFIG["keywords"]
LOCATION = NAUKRI_V2_CONFIG["location"]
EXPERIENCE = NAUKRI_V2_CONFIG["experience"]
JOB_AGE = NAUKRI_V2_CONFIG.get("job_age", 1)
PROFILE_DIR = NAUKRI_V2_CONFIG["chrome_profile_dir"]

NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    return webdriver.Chrome(options=options)


def is_logged_in(driver):
    """Check whether the Naukri session is active by hitting a page that requires auth."""
    driver.get(NAUKRI_PROFILE_URL)
    time.sleep(3)

    current_url = driver.current_url.lower()
    if "nlogin" in current_url or "login" in current_url:
        return False
    return True


def wait_for_manual_login(driver, timeout=600):
    """Wait up to 10 minutes for manual login."""
    start = time.time()

    while time.time() - start < timeout:
        current_url = driver.current_url.lower()

        if "mnjuser" in current_url and "login" not in current_url:
            logger.info("Naukri (v2) login successful.")
            return True

        time.sleep(3)

    return False


def ensure_login(driver):
    if is_logged_in(driver):
        logger.info("Naukri (v2) already logged in.")
        return True

    logger.info("Naukri (v2) login required.")
    driver.get(NAUKRI_LOGIN_URL)
    logger.info("Waiting for manual Naukri login...")

    return wait_for_manual_login(driver)


def build_url(keyword, location, experience, job_age):
    slug = keyword.lower().strip().replace(" ", "-")
    loc = location.lower().strip()

    base_url = f"https://www.naukri.com/{slug}-jobs-in-{loc}"
    params = {
        "k": keyword.replace(" ", "+"),
        "l": loc,
        "experience": experience,
        "jobAge": job_age,
    }

    query_string = "&".join(f"{key}={value}" for key, value in params.items())
    return f"{base_url}?{query_string}"


def get_job_count(driver):
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "styles_h1-wrapper__mHVA1")))
    soup = BeautifulSoup(driver.page_source, "html.parser")

    count_div = soup.find("div", class_="styles_h1-wrapper__mHVA1")
    if not count_div:
        return 0

    count_span = count_div.find("span", class_="styles_count-string__DlPaZ")
    count_text = count_span.text if count_span else ""
    match = re.search(r"of (\d+)", count_text)
    return int(match.group(1)) if match else 0


def extract_job_cards(soup, seen_urls, seen_job_ids):
    """Parse job cards from the current page, skipping anything already seen."""
    job_card_data = []
    job_cards = soup.find_all("div", class_="srp-jobtuple-wrapper")

    for job_card in job_cards:
        job_title_tag = job_card.find("a", class_="title", href=True)
        if not job_title_tag:
            continue

        job_header = job_title_tag.get("title", "").strip()
        job_link = job_title_tag["href"]
        if not job_link:
            continue

        hash_url = hash_job_url(job_link)
        if job_link in seen_urls or is_passed(hash_url) or job_exists(job_link):
            continue

        seen_urls.add(job_link)
        mark_passed(hash_url)

        company_name = None
        selectors = [
            ("a", "comp-name mw-25"),
            ("span", "rm-cursor-pointer comp-dtls-wrap"),
            ("span", " comp-dtls-wrap"),
        ]
        for tag, class_name in selectors:
            try:
                candidate = job_card.find(tag, class_=class_name)
                if candidate and candidate.find("a"):
                    company_name = candidate.find("a").text
                    break
                if candidate:
                    company_name = candidate.text
                    break
            except AttributeError:
                continue

        job_description_tag = job_card.find(
            "span",
            class_="job-desc ni-job-tuple-icon ni-job-tuple-icon-srp-description",
        )
        job_description = job_description_tag.text if job_description_tag else ""

        if job_link and job_header and company_name:
            job_id = get_job_id(job_header, company_name, job_description)
            if job_id in seen_job_ids:
                continue
            seen_job_ids.add(job_id)

        job_card_data.append(
            {
                "job_url": job_link,
                "job_title": job_header,
                "company_name": company_name,
                "job_description": job_description,
            }
        )

    return job_card_data


def go_to_next_page(driver):
    """Click the pagination 'Next' link. Returns False if disabled or not found."""
    try:
        next_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[text()='Next']/parent::a"))
        )
        if "disabled" in next_btn.get_attribute("outerHTML"):
            return False

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
        driver.execute_script("arguments[0].click();", next_btn)
        WebDriverWait(driver, 10).until(EC.staleness_of(next_btn))
        return True
    except Exception:
        return False


def fetch_job_details(job_link, driver):
    driver.get(job_link)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "styles_jd-header-title__rZwM1")))
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "styles_JDC__dang-inner-html__h0K4t"))
    )
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "styles_jhc__exp__k_giM")))
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "styles_jhc__location__W_pVs")))

    soup = BeautifulSoup(driver.page_source, "html.parser")

    exp_div = soup.find("div", class_="styles_jhc__exp__k_giM")
    experience = exp_div.find("span").text if exp_div else "Experience not found"

    job_title_div = soup.find("h1", class_="styles_jd-header-title__rZwM1")
    job_title = job_title_div.text if job_title_div else "Job title not found"

    company_div = soup.select_one("div[class*='jd-header-comp-name']")
    company_name = None
    if company_div:
        a_tag = company_div.find("a")
        span_tag = company_div.find("span")
        if a_tag:
            company_name = a_tag.get_text(strip=True)
        elif span_tag:
            company_name = span_tag.get_text(strip=True)

    location_div = soup.find("span", class_="styles_jhc__location__W_pVs")
    location = location_div.find("a").text if location_div else "Location not found"

    job_description_div = soup.find("div", class_="styles_JDC__dang-inner-html__h0K4t")
    job_description = job_description_div.text if job_description_div else "Job description not found"

    return experience, job_title, company_name, location, job_description


def naukri_v2():
    """
    Logged-in Naukri scraper, wired into the same pipeline (queue, dedup,
    storage, logging) as the original Naukri() in naukri.py. Run both
    side-by-side; they use separate Chrome profiles so they won't conflict.
    """
    driver = create_driver()
    register_driver(driver)
    seen_urls = set()
    seen_job_ids = set()

    try:
        if not ensure_login(driver):
            logger.warning("Naukri (v2) login timeout. Stopping.")
            return

        while True:
            total_jobs_found = 0
            fresh_jobs = 0
            cycle_start = time.time()

            try:
                for keyword in JOB_KEYWORDS:
                    iteration_start = time.time()
                    iteration_jobs_found = 0
                    iteration_fresh_jobs = 0
                    url = build_url(keyword, LOCATION, EXPERIENCE, JOB_AGE)

                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "styles_h1-wrapper__mHVA1"))
                    )

                    total_available_jobs = get_job_count(driver)
                    pages_to_visit = max(1, ceil(total_available_jobs / 20))
                    collected_job_cards = []

                    for _ in range(pages_to_visit):
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "srp-jobtuple-wrapper"))
                        )
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        page_job_cards = extract_job_cards(soup, seen_urls, seen_job_ids)
                        collected_job_cards.extend(page_job_cards)
                        iteration_jobs_found += len(page_job_cards)

                        if not go_to_next_page(driver):
                            break

                    for job_card_data in collected_job_cards:
                        try:
                            experience, job_title, company_name, location, job_description = fetch_job_details(
                                job_card_data["job_url"],
                                driver,
                            )
                            job_data = {
                                "job_url": job_card_data["job_url"],
                                "experience_required": experience,
                                "job_title": job_title,
                                "company_name": company_name,
                                "location": location,
                                "job_description": job_description,
                                "source": SOURCE_LABEL,
                            }

                            if enqueue_job(job_data):
                                iteration_fresh_jobs += 1
                                fresh_jobs += 1
                        except Exception:
                            logger.exception(
                                "Naukri (v2) job detail fetch failed | keyword=%s | job=%s",
                                keyword,
                                job_card_data["job_url"],
                            )

                    total_jobs_found += iteration_jobs_found
                    log_iteration_summary(
                        logger,
                        "Naukri-v2",
                        f"keyword='{keyword}' location='{LOCATION}'",
                        iteration_jobs_found,
                        iteration_fresh_jobs,
                        time.time() - iteration_start,
                    )

                time.sleep(random.uniform(2, 4))
            except Exception:
                logger.exception("Naukri (v2) fatal cycle error. Recreating driver.")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(random.uniform(20, 60))
                driver = create_driver()
                if not ensure_login(driver):
                    logger.warning("Naukri (v2) login timeout after driver recreation. Stopping.")
                    break
            finally:
                log_cycle_summary(
                    logger,
                    "Naukri-v2",
                    total_jobs_found,
                    fresh_jobs,
                    time.time() - cycle_start,
                )
    except KeyboardInterrupt:
        logger.info("Naukri (v2) shutting down.")
    finally:
        driver.quit()


if __name__ == "__main__":
    naukri_v2()
