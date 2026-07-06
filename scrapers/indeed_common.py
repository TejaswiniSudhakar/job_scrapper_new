"""Shared helpers for Indeed scrapers (v1 and v2).

Both indeed.py and indeed_v2.py use identical logic for interacting with
Indeed's split-view job listing UI. This module centralises that logic so
changes only need to happen in one place.
"""

import random
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class IndeedVerificationError(Exception):
    pass


def random_pause(min_seconds=1.0, max_seconds=3.0):
    time.sleep(random.uniform(min_seconds, max_seconds))


def is_verification_page(driver):
    try:
        page_source = driver.page_source.lower()
        return "additional verification required" in page_source
    except Exception:
        return False


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
    """Extract job description using Selenium .text (not BS4) for consistent comparison."""
    elements = driver.find_elements(By.ID, "jobDescriptionText")
    if elements:
        return elements[0].text.strip()
    return ""


def wait_for_job_content(driver, previous_description="", timeout=20):
    """Wait for the job-detail panel to update after a click."""
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
        (By.XPATH, "//span[contains(text(), '\u20b9')]"),
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
