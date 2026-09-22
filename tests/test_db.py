from db import create_backup, liste_backups, load_db, neue_id, save_db


def test_load_db_erstellt_leere_db_wenn_keine_existiert():
    db = load_db()
    assert db["standorte"] == {}
    assert db["behaelter"] == {}
    assert db["items"] == {}


def test_save_und_load_roundtrip():
    db = load_db()
    sid = neue_id()
    db["standorte"][sid] = {"id": sid, "name": "Regal 1"}
    save_db(db)

    db2 = load_db()
    assert db2["standorte"][sid]["name"] == "Regal 1"


def test_neue_id_ist_eindeutig():
    ids = {neue_id() for _ in range(200)}
    assert len(ids) == 200


def test_backup_wird_nur_bei_aenderung_erstellt():
    db = load_db()
    db["standorte"][neue_id()] = {"name": "Regal 1"}
    save_db(db)

    erstes_backup = create_backup()
    assert erstes_backup is not None
    assert erstes_backup.exists()

    zweites_backup = create_backup()
    assert zweites_backup is None  # keine Änderung seit dem letzten Backup


def test_backup_force_erstellt_immer():
    create_backup()
    anzahl_vorher = len(liste_backups())
    ziel = create_backup(force=True)
    assert ziel is not None
    assert len(liste_backups()) == anzahl_vorher + 1
