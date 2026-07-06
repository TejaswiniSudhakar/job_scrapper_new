# services/driver_registry.py
import threading
import threading
UC_INIT_LOCK = threading.Lock()
_lock = threading.Lock()
_drivers = []

def register_driver(driver):
    with _lock:
        _drivers.append(driver)
    print(f"Driver {driver} registered successfully. Total drivers: {len(_drivers)}")

def quit_all_drivers():
    with _lock:
        for driver in _drivers:
            try:
                driver.quit()
                print(f"Driver {driver} quit successfully.")
            except Exception as e:
                print(f"Error occurred while quitting driver {driver}: {e}")
        _drivers.clear()