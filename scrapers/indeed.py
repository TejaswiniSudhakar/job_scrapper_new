import re
import subprocess
import time

from services.driver_registry import register_driver, UC_INIT_LOCK
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import APP_CONFIG
from pipeline.deduplicator import get_job_id, hash_job_url, is_passed, is_seen, mark_passed
from queue_manager import enqueue_job
from scrapers.indeed_common import (
    IndeedVerificationError,
    find_job_link_element,
    get_company_name,
    get_detail_location,
    get_job_description,
    get_next_page_button,
    get_salary,
    get_visible_job_links,
    human_move_and_click,
    human_scroll,
    is_verification_page,
    random_pause,
    wait_for_job_content,
)
from services.logging_utils import get_logger, log_cycle_summary, log_iteration_summary
from services.storage import job_exists


logger = get_logger("scraper.indeed")
SCRAPER_CONFIG = APP_CONFIG["scrapers"]
INDEED_CONFIG = SCRAPER_CONFIG["indeed"]
SOURCE_LABEL = "Indeed"

JOB_KEYWORDS = SCRAPER_CONFIG["keywords"]
LOCATION = INDEED_CONFIG["location"]

# How many keywords to run before taking a longer break. Keeps total
# automated traffic per "burst" lower, which matters more for fingerprint-
# based bot detection than per-click pacing does.
KEYWORDS_PER_BATCH = 5



def _get_chrome_major_version():
    """Reads the installed Chrome version from the registry on Windows."""
    for hive in (
        r"HKLM\SOFTWARE\Google\Chrome\BLBeacon",
        r"HKCU\SOFTWARE\Google\Chrome\BLBeacon",
    ):
        try:
            out = subprocess.check_output(
                f'reg query "{hive}" /v version',
                shell=True,
                stderr=subprocess.DEVNULL,
            ).decode()
            match = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
            if match:
                return int(match.group(1))
        except Exception:
            pass
    return None  # let UC decide


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={INDEED_CONFIG['chrome_profile_dir']}")
    options.add_argument(f"--profile-directory={INDEED_CONFIG['chrome_profile_name']}")

    with UC_INIT_LOCK:
        driver = uc.Chrome(version_main=_get_chrome_major_version(), options=options)
    register_driver(driver)
    return driver



def Indeed(source_label=SOURCE_LABEL):
    driver = create_driver()
    seen_urls = set()

    try:
        while True:
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
                        f"&fromage={INDEED_CONFIG['days_old']}&radius={INDEED_CONFIG['radius']}"
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
                                        "source": source_label,
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

            except Exception:
                logger.exception("Indeed fatal cycle error. Recreating driver.")
                try:
                    driver.quit()
                except Exception:
                    pass
                random_pause(20.0, 60.0)
                driver = create_driver()

            finally:
                log_cycle_summary(
                    logger,
                    "Indeed",
                    total_jobs_found,
                    fresh_jobs,
                    time.time() - cycle_start,
                )

    except KeyboardInterrupt:
        logger.info("Indeed shutting down.")
        driver.quit()