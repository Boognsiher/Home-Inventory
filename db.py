"""Persistenz-Layer: JSON-Datei via load_db/save_db-Pattern (keine SQL-DB).

Alle Schreibzugriffe laufen über open_db() als Context-Manager, der die
Datei atomar (Temp-Datei + Replace) schreibt und mit einem Lock gegen
gleichzeitige Requests absichert.
"""

import hashlib
import json
import threading
import zipfile
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from config import Config

_lock = threading.RLock()

LEERE_DB = {
    "standorte": {},
    "behaelter": {},
    "items": {},
    "meta": {"erstellt": None, "letztes_backup": None, "backup_hash": None},
}


def neue_id():
    return uuid4().hex[:12]


def load_db():
    Config.ensure_dirs()
    if not Config.DB_PATH.exists():
        db = json.loads(json.dumps(LEERE_DB))
        db["meta"]["erstellt"] = datetime.now().isoformat()
        save_db(db)
        return db
    with open(Config.DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    db.setdefault("standorte", {})
    db.setdefault("behaelter", {})
    db.setdefault("items", {})
    db.setdefault("meta", {})
    return db


def save_db(db):
    Config.ensure_dirs()
    tmp_path = Config.DB_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    tmp_path.replace(Config.DB_PATH)


@contextmanager
def open_db():
    """Atomarer Lese-/Schreibzugriff auf die Inventar-DB.

    with open_db() as db:
        db["items"][id]["menge"] -= 1
    # wird beim Verlassen automatisch gespeichert
    """
    with _lock:
        db = load_db()
        yield db
        save_db(db)


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _inhalts_hash(db):
    roh = json.dumps(
        {"standorte": db["standorte"], "behaelter": db["behaelter"], "items": db["items"]},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()


def backup_noetig():
    """True, wenn sich das Inventar seit dem letzten Backup geändert hat."""
    db = load_db()
    return _inhalts_hash(db) != db["meta"].get("backup_hash")


def create_backup(force=False):
    """Erstellt ein ZIP-Backup (inventory.json + Fotos), wenn nötig.

    Gibt den Pfad des neuen Backups zurück, oder None wenn übersprungen
    (keine Änderung seit dem letzten Backup und force=False).
    """
    with _lock:
        Config.ensure_dirs()
        db = load_db()
        aktueller_hash = _inhalts_hash(db)

        if not force and aktueller_hash == db["meta"].get("backup_hash"):
            return None

        zeitstempel = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        ziel = Config.BACKUP_DIR / f"backup_{zeitstempel}.zip"

        with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(Config.DB_PATH, arcname="inventory.json")
            for datei in sorted(Config.UPLOAD_DIR.glob("*")):
                if datei.is_file():
                    zf.write(datei, arcname=f"uploads/{datei.name}")

        db["meta"]["letztes_backup"] = datetime.now().isoformat()
        db["meta"]["backup_hash"] = aktueller_hash
        save_db(db)

        _backups_aufraeumen()
        return ziel


def _backups_aufraeumen(keep=None):
    keep = keep or Config.BACKUP_KEEP
    backups = sorted(Config.BACKUP_DIR.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime)
    while len(backups) > keep:
        backups.pop(0).unlink(missing_ok=True)


def liste_backups():
    if not Config.BACKUP_DIR.exists():
        return []
    return sorted(Config.BACKUP_DIR.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
