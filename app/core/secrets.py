import keyring
import keyring.errors

from core.config import KEYRING_SERVICE_NAME, KEYRING_TOKEN_USERNAME


def get_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_TOKEN_USERNAME)


def set_token(token: str) -> None:
    keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_TOKEN_USERNAME, token)


def delete_token() -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE_NAME, KEYRING_TOKEN_USERNAME)
    except keyring.errors.PasswordDeleteError:
        pass


def has_token() -> bool:
    return bool(get_token())
