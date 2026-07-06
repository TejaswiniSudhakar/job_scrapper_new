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
from queue_manager import enqueue_job
from scrapers.naukri_common import extract_job_cards, go_to_next_page
from services.driver_registry import register_driver
from services.logging_utils import get_logger, log_cycle_summary, log_iteration_summary


logger = get_logger("scraper.naukri")
SCRAPER_CONFIG = APP_CONFIG["scrapers"]
NAUKRI_CONFIG = SCRAPER_CONFIG["naukri"]
SOURCE_LABEL = "Naukri"

JOB_KEYWORDS = SCRAPER_CONFIG["keywords"]
LOCATION = NAUKRI_CONFIG["location"]
EXPERIENCE = NAUKRI_CONFIG["experience"]


def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={NAUKRI_CONFIG['chrome_profile_dir']}")
    return webdriver.Chrome(options=options)


def fetch_job_details(job_link, driver):
    driver.get(job_link)

    # All four waits use partial-class XPath so they survive Naukri
    # frontend redeploys that regenerate CSS-module hashes.
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(@class,'jd-header-title')]"))
    )
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(@class,'dang-inner-html')]"))
    )
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(@class,'jhc__exp')]"))
    )
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(@class,'jhc__location')]"))
    )

    soup = BeautifulSoup(driver.page_source, "html.parser")

    exp_div = soup.find(lambda t: t.name == "div" and any("jhc__exp" in c for c in t.get("class", [])))
    experience = exp_div.find("span").text if exp_div else "Experience not found"

    job_title_div = soup.find(lambda t: t.name == "h1" and any("jd-header-title" in c for c in t.get("class", [])))
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

    location_div = soup.find(lambda t: t.name == "span" and any("jhc__location" in c for c in t.get("class", [])))
    location = location_div.find("a").text if location_div else "Location not found"

    job_description_div = soup.find(lambda t: t.name == "div" and any("dang-inner-html" in c for c in t.get("class", [])))
    job_description = job_description_div.text if job_description_div else "Job description not found"

    return experience, job_title, company_name, location, job_description


def build_url(keyword, location, exp):
    slug = keyword.lower().replace(" ", "-")
    loc = location.lower()
    query_keyword = keyword.replace(" ", "+")
    url = f"https://www.naukri.com/{slug}-jobs-in-{loc}"
    return f"{url}?k={query_keyword}&l={loc}&experience={exp}&jobAge=2"


def get_job_count(driver):
    # Naukri uses CSS-module class names (e.g. styles_count-string__DlPaZ)
    # that change on every frontend deploy. Use a partial-class XPath so
    # the selector survives redeploys.
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(@class,'count-string')]")
            )
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        count_span = soup.find(lambda tag: tag.name == "span" and "count-string" in " ".join(tag.get("class", [])))
        count_text = count_span.text if count_span else ""
        match = re.search(r"of (\d+)", count_text)
        if match:
            return int(match.group(1))
    except Exception:
        pass

    # Fallback: count visible job cards on the first page and assume
    # there are enough pages to paginate through rather than stopping early.
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="srp-jobtuple-wrapper")
        return len(cards) if cards else 0
    except Exception:
        return 0



def Naukri():
    driver = create_driver()
    register_driver(driver)
    seen_urls = set()
    seen_job_ids = set()

    try:
        while True:
            total_jobs_found = 0
            fresh_jobs = 0
            cycle_start = time.time()

            try:
                for keyword in JOB_KEYWORDS:
                    iteration_start = time.time()
                    iteration_jobs_found = 0
                    iteration_fresh_jobs = 0
                    url = build_url(keyword, LOCATION, EXPERIENCE)

                    driver.get(url)
                    # Wait for job cards — more stable than the count header
                    # whose CSS-module class name changes on every Naukri deploy.
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "srp-jobtuple-wrapper")
                        )
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
                            logger.exception("Naukri job detail fetch failed | keyword=%s | job=%s", keyword, job_card_data["job_url"])

                    total_jobs_found += iteration_jobs_found
                    log_iteration_summary(
                        logger,
                        "Naukri",
                        f"keyword='{keyword}' location='{LOCATION}'",
                        iteration_jobs_found,
                        iteration_fresh_jobs,
                        time.time() - iteration_start,
                    )

                time.sleep(random.uniform(2, 4))
            except Exception:
                logger.exception("Naukri fatal cycle error. Recreating driver.")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(random.uniform(20, 60))
                driver = create_driver()
            finally:
                log_cycle_summary(
                    logger,
                    "Naukri",
                    total_jobs_found,
                    fresh_jobs,
                    time.time() - cycle_start,
                )
    except KeyboardInterrupt:
        logger.info("Naukri shutting down.")
        driver.quit()
