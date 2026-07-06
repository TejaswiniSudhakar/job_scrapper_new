"""Shared helpers for Naukri scrapers (v1 and v2).

Both naukri.py and naukri_v2.py use identical logic for extracting job
cards from search result pages and paginating. This module centralises
that logic.
"""

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pipeline.deduplicator import get_job_id, hash_job_url, is_passed, mark_passed
from services.storage import job_exists


def extract_job_cards(soup, seen_urls, seen_job_ids):
    """Parse job cards from a Naukri search results page, skipping duplicates."""
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
