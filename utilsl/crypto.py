import os, base64
from cryptography.fernet import Fernet

RAW_KEY = os.getenv("FERNET_KEY")           # must be 32 url-safe base64 bytes

if not RAW_KEY:
    raise RuntimeError(
        "FERNET_KEY is missing. "
        "Generate one with:  python -c 'from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())'  "
        "and add it to your .env / docker-compose."
    )

# strip optional quotes people often put in .env files
RAW_KEY = RAW_KEY.strip('"').strip("'")

try:
    FERNET = Fernet(RAW_KEY)
except (ValueError, base64.binascii.Error) as exc:
    raise RuntimeError(
        "FERNET_KEY is not valid base64; regenerate a 32-byte Fernet key."
    ) from exc


def encrypt(plain: str) -> str:
    return FERNET.encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return FERNET.decrypt(token.encode()).decode()
