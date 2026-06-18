from threading import Thread
import threading
import time
import atexit
import signal
from services.ranker import init
from scrapers.linkedIn import linkedIn
from scrapers.naukri import Naukri   # optional
from scrapers.indeed import Indeed
from services.storage import init_db
from services.logging_utils import configure_logging, get_logger
from pipeline.processor import processor
from csv_exporter import export_loop
import os
import sys
LOCK_FILE = "app.lock"
logger = get_logger("main")
shutdown_event = threading.Event()


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
            logger.warning("Another instance is already running with PID %s. Exiting.", existing_pid)
            sys.exit(0)

        logger.warning("Removing stale lock file for PID %s.", existing_pid)
        release_lock()

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def request_shutdown(signum=None, frame=None):
    logger.info("Shutdown requested%s.", f" by signal {signum}" if signum else "")
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

def start_system():
    configure_logging()
    logger.info("Starting job automation system.")
    # ---- Initialize Database ----
    init_db()
    init()
    # ---- Start Processor (Consumer) ----
    processor_thread = Thread(
        target=processor,
        daemon=True
    )
    processor_thread.start()
    logger.info("Processor started.")

    # ---- Start LinkedIn Scraper ----
    linkedin_thread = threading.Thread(target=linkedIn, daemon=True)
    linkedin_thread.start()
    logger.info("LinkedIn scraper started.")

    # ---- Start CSV Exporter ----
    csv_thread = threading.Thread(target=export_loop, daemon=True)
    csv_thread.start()
    logger.info("CSV exporter started.")

    naukri_thread = Thread(
        target=Naukri,
        daemon=True
    )
    naukri_thread.start()
    logger.info("Naukri scraper started.")

    indeed_thread = Thread(
        target=Indeed,
        daemon=True
    )
    indeed_thread.start()
    logger.info("Indeed scraper started.")

    # ---- Keep Main Alive ----
    while not shutdown_event.is_set():
        time.sleep(1)

    logger.info("Shutting down system.")

if __name__ == "__main__":
    install_shutdown_handlers()
    acquire_lock()

    try:
        start_system()
    finally:
        release_lock()
