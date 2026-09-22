import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Muss VOR dem Import von config/app gesetzt werden, da Config.DATA_DIR
# beim Modul-Import ausgewertet wird.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="werkstatt_test_")
os.environ["DISABLE_BACKUP_SCHEDULER"] = "1"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import db as db_module  # noqa: E402


@pytest.fixture(autouse=True)
def _leere_datenbank():
    """Setzt die Test-Datenbank vor jedem Test auf einen leeren Zustand zurück."""
    leer = json.loads(json.dumps(db_module.LEERE_DB))
    leer["meta"]["erstellt"] = datetime.now().isoformat()
    db_module.save_db(leer)
    yield


@pytest.fixture
def client():
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c
