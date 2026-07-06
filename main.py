
from threading import Thread
import threading
import time
import atexit
import signal
import os
import sys

from services.driver_registry import quit_all_drivers
from services.ranker import init
from services.storage import init_db, cleanup_old_jobs
from services.logging_utils import configure_logging, get_logger

from pipeline.processor import processor
from csv_exporter import export_loop

from scrapers.linkedIn import linkedIn
from scrapers.linkedin_v2 import linkedin_v2
from scrapers.naukri import Naukri
from scrapers.naukri_v2 import naukri_v2
from scrapers.indeed import Indeed
from scrapers.indeed_v2 import indeed_v2

LOCK_FILE = "app.lock"

logger = get_logger("main")
shutdown_event = threading.Event()


SCRAPERS = {
    "1": ("LinkedIn", linkedIn),
    "2": ("LinkedIn v2", linkedin_v2),
    "3": ("Naukri", Naukri),
    "4": ("Naukri v2", naukri_v2),
    "5": ("Indeed", Indeed),
    "6": ("Indeed v2", indeed_v2),
}


def is_process_running(pid):
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                existing_pid = int(f.read().strip())
        except (OSError, ValueError):
            existing_pid = -1

        if is_process_running(existing_pid):
            logger.warning(
                "Another instance is already running with PID %s. Exiting.",
                existing_pid
            )
            sys.exit(0)

        logger.warning(
            "Removing stale lock file for PID %s.",
            existing_pid
        )
        release_lock()

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def request_shutdown(signum=None, frame=None):
    logger.info(
        "Shutdown requested%s.",
        f" by signal {signum}" if signum else ""
    )
    shutdown_event.set()


def install_shutdown_handlers():
    atexit.register(release_lock)

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(signum, request_shutdown)
        except (AttributeError, ValueError):
            pass

    if hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, request_shutdown)
        except (AttributeError, ValueError):
            pass


def select_scrapers():
    print("\nAvailable Scrapers")
    print("-" * 50)

    for key, (name, _) in SCRAPERS.items():
        print(f"{key}. {name}")

    print("\nSpecial Options")
    print("-" * 50)
    print("all  -> Run all scrapers")
    print("none -> Run only processor/exporter")

    choice = input(
        "\nSelect scrapers (example: 2,4,6): "
    ).strip().lower()

    if choice == "all":
        return list(SCRAPERS.values())

    if choice in ("none", ""):
        return []

    selected = []

    for item in choice.split(","):
        item = item.strip()

        if item in SCRAPERS:
            selected.append(SCRAPERS[item])
        else:
            print(f"Skipping invalid option: {item}")

    return selected


def start_system():
    configure_logging()

    logger.info("Starting job automation system.")

    # Initialize DB / Ranking
    init_db()
    cleanup_old_jobs()
    init()

    # Processor
    processor_thread = Thread(
        target=processor,
        daemon=True,
        name="Processor"
    )
    processor_thread.start()

    logger.info("Processor started.")

    # CSV Exporter
    csv_thread = Thread(
        target=export_loop,
        daemon=True,
        name="CSVExporter"
    )
    csv_thread.start()

    logger.info("CSV exporter started.")

    # Select Scrapers
    selected_scrapers = select_scrapers()

    if not selected_scrapers:
        logger.info("No scrapers selected.")
    else:
        logger.info(
            "Starting %d scraper(s)...",
            len(selected_scrapers)
        )

    scraper_threads = []

    for scraper_name, scraper_func in selected_scrapers:
        thread = Thread(
            target=scraper_func,
            daemon=True,
            name=scraper_name
        )

        thread.start()
        scraper_threads.append(thread)

        logger.info("%s scraper started.", scraper_name)

    # Keep Main Alive
    try:
        while not shutdown_event.is_set():
            time.sleep(1)

    finally:
        logger.info("Shutting down system.")

        quit_all_drivers()

        time.sleep(2)

        logger.info("Shutdown complete.")


if __name__ == "__main__":
    install_shutdown_handlers()
    acquire_lock()

    try:
        start_system()
    finally:
        release_lock()
