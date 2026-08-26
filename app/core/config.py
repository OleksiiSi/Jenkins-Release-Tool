import sys
from pathlib import Path

# Directory the app's files (settings, cache) live next to.
# In a PyInstaller --onedir build this is the folder containing the
# executable; in dev mode it's the project root. sys.frozen is set by
# PyInstaller's bootloader before any of our code runs, so this is stable
# for the lifetime of the process - safe to compute once at import time.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

SETTINGS_PATH = APP_DIR / "settings.json"
SETTINGS_DEFAULT_PATH = APP_DIR / "settings.default.json"
CONNECTION_CHECKS_CACHE_PATH = APP_DIR / "connection_checks_cache.json"

KEYRING_SERVICE_NAME = "jenkins-env-promotion-tool"
KEYRING_TOKEN_USERNAME = "jenkins_api_token"

# Runner's shared ThreadPoolExecutor size. Generous on purpose - it must
# exceed the worst-case number of simultaneously in-flight tasks (build
# tasks blocked on their own promotion futures, the promotion tasks
# themselves, plus the run-finished waiter task), or a run can deadlock via
# thread-pool starvation. See core/runner.py's Runner.start() docstring for
# the full accounting.
MAX_WORKERS = 20
