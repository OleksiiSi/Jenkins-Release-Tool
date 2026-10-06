import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

SETTINGS_PATH = APP_DIR / "settings.json"
SETTINGS_DEFAULT_PATH = APP_DIR / "settings.default.json"
CONNECTION_CHECKS_CACHE_PATH = APP_DIR / "connection_checks_cache.json"

KEYRING_SERVICE_NAME = "jenkins-env-promotion-tool"
KEYRING_TOKEN_USERNAME = "jenkins_api_token"

MAX_WORKERS = 20
