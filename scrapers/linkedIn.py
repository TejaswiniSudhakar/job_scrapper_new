import random
import time
from queue import Full
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
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


logger = get_logger("scraper.linkedin")
SCRAPER_CONFIG = APP_CONFIG["scrapers"]
LINKEDIN_CONFIG = SCRAPER_CONFIG["linkedin"]
SOURCE_LABEL = "LinkedIn"

JOB_KEYWORDS = SCRAPER_CONFIG["keywords"]
COUNTRIES = LINKEDIN_CONFIG["locations"]
DATE_POSTED = LINKEDIN_CONFIG["date_posted"]
MAX_SCROLLS = LINKEDIN_CONFIG["max_scrolls"]


def build_linkedin_url(keyword, location):
    date_param = ""
    if DATE_POSTED == "24h":
        date_param = "r86400"
    elif DATE_POSTED == "week":
        date_param = "r604800"
    elif DATE_POSTED == "month":
        date_param = "r2592000"

    return (
        "https://www.linkedin.com/jobs/search/?"
        f"keywords={quote_plus(keyword)}"
        f"&location={quote_plus(location)}"
        f"&f_E=2%2C3"
        f"&f_TPR={date_param}"
    )


def is_no_results(driver):
    try:
        msg = driver.find_element(By.CSS_SELECTOR, "section.no-results h1").text
        return "couldn’t find a match" in msg.lower()
    except Exception:
        return False



def get_total_jobs(driver):
    try:
        count_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "results-context-header__job-count"))
        )
        return int(count_element.text.strip().replace(",", ""))
    except Exception:
        logger.warning("LinkedIn job count not available for current page.")
        return 0


def close_popup(driver):
    try:
        close_btn = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.contextual-sign-in-modal__modal-dismiss"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", close_btn)
        driver.execute_script("arguments[0].click();", close_btn)
    except Exception:
        return


def scroll_until_end(driver, refresh_max, max_idle=5):
    if refresh_max == 0:
        return

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    idle_rounds = 0
    clicks = 0
    last_height = None
    close_popup(driver)

    while clicks < MAX_SCROLLS:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        try:
            button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'infinite-scroller__show-more-button')]"))
            )
            driver.execute_script("arguments[0].click();", button)
            clicks += 1
            idle_rounds = 0
            time.sleep(2)
        except Exception:
            pass

        try:
            end_msg = driver.find_element(By.XPATH, "//p[contains(text(), \"You've viewed all jobs\")]")
            if end_msg.is_displayed():
                break
        except Exception:
            pass

        new_height = driver.execute_script("return document.body.scrollHeight")
        if last_height is not None and new_height == last_height:
            idle_rounds += 1
        else:
            idle_rounds = 0

        if idle_rounds >= max_idle:
            driver.get(driver.current_url)
            if refresh_max > 1:
                scroll_until_end(driver, refresh_max - 1, max_idle)
            break

        last_height = new_height


def fetch_job_details(driver, job_url, retry):
    if retry == 0:
        logger.warning("LinkedIn max retries reached for job details: %s", job_url)
        return "", ""

    try:
        driver.get(job_url)
        time.sleep(random.uniform(2, 4))
        soup = BeautifulSoup(driver.page_source, "html.parser")

        job_div = soup.find("div", class_="description__text")
        company_div = soup.find("div", class_="show-more-less-html__markup")

        job_desc = job_div.get_text(separator="\n", strip=True) if job_div else ""
        company_desc = company_div.get_text(separator="\n", strip=True) if company_div else ""

        if job_desc or company_desc:
            return job_desc, company_desc
    except Exception:
        logger.exception("LinkedIn job detail error for %s", job_url)

    time.sleep(random.uniform(2, 4))
    return fetch_job_details(driver, job_url, retry - 1)


def linkedIn():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--incognito")

    driver = webdriver.Chrome(options=options)
    register_driver(driver)

    try:
        seen_urls = set()

        while True:
            total_jobs_found = 0
            fresh_jobs = 0
            cycle_start = time.time()

            try:
                for keyword in JOB_KEYWORDS:
                    for country in COUNTRIES:
                        iteration_start = time.time()
                        iteration_jobs_found = 0
                        iteration_fresh_jobs = 0
                        url = build_linkedin_url(keyword, country)

                        driver.get(url)
                        time.sleep(random.uniform(2, 4))
                        if is_no_results(driver):
                            log_iteration_summary(
                                logger,
                                "LinkedIn",
                                f"keyword='{keyword}' location='{country}'",
                                0,
                                0,
                                time.time() - iteration_start,
                            )
                            continue

                        scroll_until_end(driver, 5)
                        time.sleep(random.uniform(2, 3))

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        job_cards = soup.find_all("div", class_="base-card")
                        expected_jobs = get_total_jobs(driver)

                        iteration_jobs_found = len(job_cards)
                        total_jobs_found += iteration_jobs_found
                        if expected_jobs and iteration_jobs_found > expected_jobs:
                            logger.info(
                                "LinkedIn fetched more visible cards than expected count | keyword=%s | location=%s | visible=%s | expected=%s",
                                keyword,
                                country,
                                iteration_jobs_found,
                                expected_jobs,
                            )

                        for card in job_cards:
                            try:
                                link = card.find("a", class_="base-card__full-link")
                                if not link:
                                    continue

                                job_url = link["href"].split("?")[0]
                                url_hash = hash_job_url(job_url)
                                if job_url in seen_urls or is_passed(url_hash) or job_exists(job_url):
                                    continue

                                seen_urls.add(job_url)
                                mark_passed(url_hash)

                                title_span = link.find("span")
                                job_title = title_span.text.strip() if title_span else ""

                                company_tag = card.find("h4", class_="base-search-card__subtitle")
                                company_a = company_tag.find("a") if company_tag else None
                                company_name = company_a.text.strip() if company_a else ""

                                location_tag = card.find("span", class_="job-search-card__location")
                                location = location_tag.text.strip() if location_tag else ""

                                job_description, _company_description = fetch_job_details(driver, job_url, 5)
                                experience = get_experience_from_description(job_description + job_title)

                                job_data = {
                                    "job_url": job_url,
                                    "experience_required": experience,
                                    "job_title": job_title,
                                    "company_name": company_name,
                                    "location": location,
                                    "job_description": job_description,
                                    "source": SOURCE_LABEL,
                                }

                                try:
                                    if enqueue_job(job_data):
                                        iteration_fresh_jobs += 1
                                        fresh_jobs += 1
                                except Full:
                                    logger.warning("LinkedIn queue full while adding: %s", job_title)
                            except Exception:
                                logger.exception(
                                    "LinkedIn job parsing failed | keyword=%s | location=%s",
                                    keyword,
                                    country,
                                )
                            time.sleep(random.uniform(1.5, 3))

                        log_iteration_summary(
                            logger,
                            "LinkedIn",
                            f"keyword='{keyword}' location='{country}'",
                            iteration_jobs_found,
                            iteration_fresh_jobs,
                            time.time() - iteration_start,
                        )

                time.sleep(random.uniform(10, 60))
            except Exception:
                logger.exception("LinkedIn fatal cycle error. Recreating driver.")
                try:
                    driver.quit()
                except Exception:
                    pass

                options = Options()
                options.add_argument("--start-maximized")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--incognito")
                driver = webdriver.Chrome(options=options)
            finally:
                log_cycle_summary(
                    logger,
                    "LinkedIn",
                    total_jobs_found,
                    fresh_jobs,
                    time.time() - cycle_start,
                )
    except KeyboardInterrupt:
        logger.info("LinkedIn shutting down.")
        driver.quit()
