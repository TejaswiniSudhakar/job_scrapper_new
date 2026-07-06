import random
import time
import threading

import undetected_chromedriver as uc
from services.driver_registry import register_driver, UC_INIT_LOCK

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import APP_CONFIG
from pipeline.deduplicator import get_job_id, hash_job_url, is_passed, is_seen, mark_passed
from queue_manager import enqueue_job
from services.logging_utils import configure_logging, get_logger, log_cycle_summary, log_iteration_summary
from services.storage import job_exists

# Resolved at runtime to avoid a circular import — main sets this event
# when it receives SIGINT/SIGTERM so all scraper threads can exit cleanly.
def _get_shutdown_event():
    try:
        import __main__
        return getattr(__main__, "shutdown_event", None)
    except Exception:
        return None


logger = get_logger("scraper.indeed_v2")
SCRAPER_CONFIG = APP_CONFIG["scrapers"]
INDEED_V2_CONFIG = SCRAPER_CONFIG["indeed_v2"]

JOB_KEYWORDS = SCRAPER_CONFIG["keywords"]
LOCATION = INDEED_V2_CONFIG["location"]

# How many keywords to run before taking a longer break. Keeps total
# automated traffic per "burst" lower, which matters more for fingerprint-
# based bot detection than per-click pacing does.
KEYWORDS_PER_BATCH = 5

# --- Logged-in session config -----------------------------------------
# v1 (anonymous) and v2 (logged-in) use separate Chrome user-data-dirs
# (configured under scrapers.indeed_v2 in config.py), since Chrome locks
# a user-data-dir to a single running instance regardless of
# --profile-directory.
INDEED_V2_PROFILE_DIR = INDEED_V2_CONFIG["chrome_profile_dir"]
INDEED_V2_PROFILE_NAME = INDEED_V2_CONFIG["chrome_profile_name"]

LOGIN_URL = "https://secure.indeed.com/account/login"
LOGIN_CHECK_URL = "https://www.indeed.com/myjobs"
LOGIN_POLL_INTERVAL = 5.0
LOGIN_TIMEOUT_SECONDS = 600  # how long to wait for manual login before giving up


class IndeedVerificationError(Exception):
    pass


class IndeedLoginTimeoutError(Exception):
    pass


def random_pause(min_seconds=1.0, max_seconds=3.0):
    time.sleep(random.uniform(min_seconds, max_seconds))


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={INDEED_V2_PROFILE_DIR}")
    options.add_argument(f"--profile-directory={INDEED_V2_PROFILE_NAME}")

    with UC_INIT_LOCK:
        driver = uc.Chrome(version_main=149, options=options)
    register_driver(driver)
    return driver


def is_verification_page(driver):
    try:
        page_source = driver.page_source.lower()
        strong_markers = ["additional verification required"]
        return any(marker in page_source for marker in strong_markers)
    except Exception:
        return False


# --- Login detection / manual-login flow --------------------------------

def is_logged_in(driver):
    """
    Checks whether the current Chrome profile has an active Indeed
    session by visiting an account-only page and inspecting both the
    resulting URL and the DOM for sign-in indicators.

    Note: Indeed's markup changes over time. If this starts
    misreporting login state, open the page in this profile and check
    what the signed-out state actually looks like, then adjust the
    markers below.
    """
    try:
        driver.get(LOGIN_CHECK_URL)
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        random_pause(2.0, 3.5)

        current_url = driver.current_url.lower()
        if "secure.indeed.com" in current_url or "/account/login" in current_url:
            return False

        page_source = driver.page_source.lower()
        signed_out_markers = [
            "sign in to view",
            ">sign in<",
            "log in to indeed",
        ]
        if any(marker in page_source for marker in signed_out_markers):
            return False

        return True
    except Exception:
        logger.exception("Indeed login check failed; assuming not logged in.")
        return False


def wait_for_manual_login(driver):
    logger.warning("Indeed session not detected. Waiting for manual login.")
    try:
        driver.get(LOGIN_URL)
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("INDEED LOGIN REQUIRED")
    print("A Chrome window is open at the Indeed sign-in page.")
    print("Please log in manually - this only needs to happen once,")
    print("since the session persists in this Chrome profile afterwards.")
    print("The scraper will resume automatically once login is detected.")
    print("=" * 60 + "\n")

    start_time = time.time()
    while time.time() - start_time < LOGIN_TIMEOUT_SECONDS:
        random_pause(LOGIN_POLL_INTERVAL, LOGIN_POLL_INTERVAL + 2)
        if is_logged_in(driver):
            logger.info("Indeed login detected. Resuming scraper.")
            print("Login detected. Resuming scraper...\n")
            return

    raise IndeedLoginTimeoutError(
        f"Manual Indeed login was not completed within {LOGIN_TIMEOUT_SECONDS} seconds."
    )


def ensure_logged_in(driver):
    if is_logged_in(driver):
        logger.info("Indeed session already active for this Chrome profile.")
        return
    wait_for_manual_login(driver)


def get_next_page_button(driver, timeout=10):
    def locate_visible_next_button(current_driver):
        buttons = current_driver.find_elements(By.XPATH, "//a[@aria-label='Next Page']")
        for button in buttons:
            try:
                if (
                    button.is_displayed()
                    and button.is_enabled()
                    and button.size["width"] > 0
                    and button.size["height"] > 0
                ):
                    return button
            except Exception:
                continue
        return False

    return WebDriverWait(driver, timeout).until(locate_visible_next_button)


def get_visible_job_links(driver):
    visible_jobs = []
    job_elements = driver.find_elements(By.XPATH, "//a[@data-jk]")

    for element in job_elements:
        try:
            job_id = element.get_attribute("data-jk")
            href = element.get_attribute("href")
            title = element.text.strip()
            if (
                job_id
                and href
                and element.is_displayed()
                and element.is_enabled()
                and element.size["width"] > 0
                and element.size["height"] > 0
            ):
                visible_jobs.append({"job_id": job_id, "href": href, "title": title})
        except Exception:
            continue

    unique_jobs = []
    seen_job_ids = set()
    for job in visible_jobs:
        if job["job_id"] not in seen_job_ids:
            seen_job_ids.add(job["job_id"])
            unique_jobs.append(job)
    return unique_jobs


def find_job_link_element(driver, job_info, timeout=10):
    job_id = job_info.get("job_id")

    def locate_job(current_driver):
        candidates = current_driver.find_elements(By.XPATH, f"//a[@data-jk='{job_id}']")
        for candidate in candidates:
            try:
                if (
                    candidate.is_displayed()
                    and candidate.is_enabled()
                    and candidate.size["width"] > 0
                    and candidate.size["height"] > 0
                ):
                    return candidate
            except Exception:
                continue
        return False

    return WebDriverWait(driver, timeout).until(locate_job)


def human_scroll(driver, target_element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
    random_pause(0.8, 1.8)
    target_y = target_element.location["y"]
    current_y = driver.execute_script("return window.pageYOffset;")

    while current_y < target_y:
        step = random.randint(150, 400)
        driver.execute_script(f"window.scrollBy(0, {step});")
        random_pause(0.4, 1.3)
        current_y += step

        if random.random() < 0.2:
            back = random.randint(50, 120)
            driver.execute_script(f"window.scrollBy(0, -{back});")
            random_pause(0.2, 0.6)

    driver.execute_script("window.scrollBy(0, 80);")
    random_pause(0.2, 0.5)


def human_move_and_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    WebDriverWait(driver, 10).until(
        lambda current_driver: element.is_displayed()
        and element.is_enabled()
        and element.size["width"] > 0
        and element.size["height"] > 0
    )
    random_pause(1.0, 2.5)
    driver.execute_script("arguments[0].click();", element)
    random_pause(1.5, 3.5)


def get_job_description(driver):
    """
    Extract the job description text from the detail panel using Selenium
    .text — NOT BeautifulSoup get_text. This must match the extraction
    method used inside wait_for_job_content so that the previous_description
    snapshot and the current_text comparison are formatted identically.
    Using different methods (BS4 vs Selenium) produces subtly different
    whitespace/newline output for the same HTML, which makes the
    != comparison unreliable and allows stale panel content to be read
    as if it were the newly-loaded job.
    """
    elements = driver.find_elements(By.ID, "jobDescriptionText")
    if elements:
        return elements[0].text.strip()
    return ""


def wait_for_job_content(driver, previous_description="", timeout=20):
    """
    Waits for the job-detail panel to update after a click.

    Indeed's split-view layout keeps the same #jobDescriptionText element
    across job switches and just swaps its inner content via JS - so
    checking for the element's *presence* isn't enough, it can already be
    there from the previously-selected job. We instead wait for the text
    inside it to be non-empty AND different from whatever was showing
    before this click, so we know the panel has actually re-rendered for
    the newly clicked job rather than still showing stale content.
    """
    def content_loaded(current_driver):
        if is_verification_page(current_driver):
            return "verification"

        description_elements = current_driver.find_elements(By.ID, "jobDescriptionText")
        if not description_elements:
            return False

        current_text = description_elements[0].text.strip()

        if current_text and current_text != previous_description:
            return "description"

        return False

    return WebDriverWait(driver, timeout).until(content_loaded)


def get_detail_location(driver):
    try:
        location_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@data-testid='inlineHeader-companyLocation']")
            )
        )
        return location_elem.text.strip()
    except Exception:
        return ""


def get_salary(driver):
    selectors = [
        (By.ID, "salaryInfoAndJobType"),
        (By.XPATH, "//div[@id='salaryInfoAndJobType']//span"),
        (By.XPATH, "//span[contains(text(), '₹')]"),
    ]
    for by, selector in selectors:
        try:
            element = driver.find_element(by, selector)
            text = element.text.strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def get_company_name(driver):
    selectors = [
        (By.XPATH, "//div[@data-testid='inlineHeader-companyName']"),
        (By.CSS_SELECTOR, "[data-testid='company-name']"),
    ]
    for by, selector in selectors:
        try:
            element = driver.find_element(by, selector)
            text = element.text.strip()
            if text:
                return text
        except Exception:
            continue
    return "Unknown"


def indeed_v2():
    driver = create_driver()
    ensure_logged_in(driver)
    seen_urls = set()

    try:
        shutdown = _get_shutdown_event()
        while not (shutdown and shutdown.is_set()):
            total_jobs_found = 0
            fresh_jobs = 0
            cycle_start = time.time()

            try:
                for keyword_index, keyword in enumerate(JOB_KEYWORDS, start=1):
                    iteration_jobs_found = 0
                    iteration_fresh_jobs = 0
                    verification_skips = 0
                    iteration_start = time.time()
                    page_number = 1
                    url = (
                        f"https://in.indeed.com/jobs?q={keyword.replace(' ', '+')}"
                        f"&l={LOCATION.replace(' ', '+').replace(',', '%2C')}"
                        f"&fromage={INDEED_V2_CONFIG['days_old']}&radius={INDEED_V2_CONFIG['radius']}"
                    )

                    driver.get(url)
                    random_pause(4.0, 7.0)

                    while True:
                        try:
                            random_pause(2.0, 5.0)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located(
                                    (By.CSS_SELECTOR, "li.css-1ac2h1w")
                                )
                            )
                            job_cards = driver.find_elements(
                                By.XPATH, "//div[contains(@class,'job_seen_beacon')]"
                            )
                            iteration_jobs_found += len(job_cards)

                            for job_info in get_visible_job_links(driver):
                                try:
                                    url_hash = hash_job_url(job_info["href"])
                                    if (
                                        job_info["href"] in seen_urls
                                        or is_passed(url_hash)
                                        or job_exists(job_info["href"])
                                    ):
                                        continue

                                    seen_urls.add(job_info["href"])

                                    # Snapshot whatever's currently rendered in the
                                    # detail panel BEFORE clicking, so we can detect
                                    # once it actually changes to this job's content.
                                    # Uses same extraction method (Selenium .text) as
                                    # wait_for_job_content so the != check is reliable.
                                    previous_description = get_job_description(driver)

                                    job = find_job_link_element(driver, job_info)
                                    human_scroll(driver, job)
                                    human_move_and_click(driver, job)

                                    load_state = wait_for_job_content(
                                        driver,
                                        previous_description=previous_description,
                                        timeout=25,
                                    )
                                    if load_state == "verification":
                                        seen_urls.discard(job_info["href"])
                                        verification_skips += 1
                                        logger.warning(
                                            "Indeed verification page detected for keyword '%s' page %s. Restarting driver.",
                                            keyword,
                                            page_number,
                                        )
                                        raise IndeedVerificationError(
                                            f"Verification page detected for keyword '{keyword}' page {page_number}"
                                        )

                                    random_pause(2.0, 4.5)
                                    description = get_job_description(driver)
                                    if not description:
                                        seen_urls.discard(job_info["href"])
                                        continue

                                    company_name = get_company_name(driver)
                                    location = get_detail_location(driver) or LOCATION
                                    salary = get_salary(driver)
                                    enriched_description = (
                                        f"Salary: {salary}\n\n{description}" if salary else description
                                    )

                                    content_job_id = get_job_id(
                                        job_info["title"], company_name, enriched_description
                                    )
                                    if is_seen(content_job_id):
                                        continue

                                    job_data = {
                                        "job_url": job_info["href"],
                                        "experience_required": "Not mentioned",
                                        "job_title": job_info["title"],
                                        "company_name": company_name,
                                        "location": location,
                                        "job_description": enriched_description,
                                        "source": "Indeed",
                                    }

                                    if job_exists(job_data["job_url"]):
                                        continue

                                    if enqueue_job(job_data):
                                        mark_passed(url_hash)
                                        iteration_fresh_jobs += 1
                                        fresh_jobs += 1
                                    else:
                                        seen_urls.discard(job_info["href"])

                                except Exception:
                                    seen_urls.discard(job_info["href"])
                                    logger.exception(
                                        "Indeed job processing failed | keyword=%s | page=%s | job=%s",
                                        keyword,
                                        page_number,
                                        job_info.get("title", "unknown"),
                                    )

                            try:
                                next_btn = get_next_page_button(driver)
                            except Exception:
                                break

                            driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", next_btn
                            )
                            random_pause(1.5, 3.5)
                            driver.execute_script("arguments[0].click();", next_btn)
                            WebDriverWait(driver, 10).until(EC.staleness_of(next_btn))
                            page_number += 1
                            random_pause(5.0, 12.0)

                        except IndeedVerificationError:
                            raise
                        except Exception:
                            logger.exception(
                                "Indeed page processing failed | keyword=%s | page=%s",
                                keyword,
                                page_number,
                            )
                            break

                    total_jobs_found += iteration_jobs_found
                    log_iteration_summary(
                        logger,
                        "Indeed",
                        f"keyword='{keyword}' verification_skips={verification_skips}",
                        iteration_jobs_found,
                        iteration_fresh_jobs,
                        time.time() - iteration_start,
                    )

                    # Longer break every few keywords, on top of the existing
                    # per-job/per-page pauses, to cap total burst traffic.
                    if keyword_index % KEYWORDS_PER_BATCH == 0 and keyword_index != len(JOB_KEYWORDS):
                        logger.info("Indeed batch break after %s keywords.", keyword_index)
                        random_pause(60.0, 180.0)

                # Longer break between full cycles (was 10-60s).
                random_pause(180.0, 420.0)

            except IndeedVerificationError as exc:
                logger.warning("Indeed driver restart requested: %s", exc)
                try:
                    driver.quit()
                except Exception:
                    pass
                random_pause(5.0, 10.0)
                driver = create_driver()
                ensure_logged_in(driver)

            except IndeedLoginTimeoutError:
                logger.exception("Indeed manual login timed out. Stopping scraper until re-run.")
                try:
                    driver.quit()
                except Exception:
                    pass
                raise

            except Exception:
                logger.exception("Indeed fatal cycle error. Recreating driver.")
                try:
                    driver.quit()
                except Exception:
                    pass
                random_pause(20.0, 60.0)
                driver = create_driver()
                ensure_logged_in(driver)

            finally:
                log_cycle_summary(
                    logger,
                    "Indeed",
                    total_jobs_found,
                    fresh_jobs,
                    time.time() - cycle_start,
                )

    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Indeed v2 shutting down.")
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    # Standalone test run: only this scraper + the bare minimum to keep
    # it from stalling (db init, and the processor thread to drain the
    # queue). Does NOT start the CSV exporter, so jobs land in the DB
    # but jobs.csv won't update during this run - run main.py for that.
    from threading import Thread

    from pipeline.processor import processor
    from services.storage import init_db

    configure_logging()
    init_db()

    processor_thread = Thread(target=processor, daemon=True)
    processor_thread.start()
    logger.info("Processor started (standalone Indeed v2 test run).")

    indeed_v2()