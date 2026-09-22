import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Zentrale Konfiguration, ausschließlich über Umgebungsvariablen gesteuert.

    Auf dem NAS werden diese Werte über die .env-Datei bzw. die
    docker-compose.yml gesetzt, damit alle persistenten Daten in einem
    einzigen gemounteten Volume (DATA_DIR) landen.
    """

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-bitte-aendern")

    DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
    UPLOAD_DIR = DATA_DIR / "uploads"
    BACKUP_DIR = DATA_DIR / "backups"
    DB_PATH = DATA_DIR / "inventory.json"

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "16")) * 1024 * 1024
    BACKUP_KEEP = int(os.environ.get("BACKUP_KEEP", "30"))
    BACKUP_STUNDE = int(os.environ.get("BACKUP_STUNDE", "3"))

    ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}

    @classmethod
    def ensure_dirs(cls):
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
