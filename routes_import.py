"""AliExpress-CSV-Import: zweistufiger Flow (Upload -> Vorschau/Bearbeiten -> Bestätigen).

Die Behälterzuordnung erfolgt pro Item manuell in der Vorschau - keine
automatische Zuordnung, da hier Nutzerurteil zählt (CLAUDE.md).
"""

import json
from datetime import datetime
from uuid import uuid4

from flask import Blueprint, render_template, request, redirect, url_for, flash

from config import Config
from csv_import import csv_parsen
from db import open_db, neue_id

bp = Blueprint("import_csv", __name__)

TMP_DIR_NAME = "import_tmp"


def _tmp_dir():
    pfad = Config.DATA_DIR / TMP_DIR_NAME
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


@bp.route("/import")
def import_upload_seite():
    return render_template("import_upload.html")


@bp.route("/import/hochladen", methods=["POST"])
def import_hochladen():
    datei = request.files.get("csv_datei")
    if not datei or not datei.filename:
        flash("Keine CSV-Datei ausgewählt", "error")
        return redirect(url_for("import_csv.import_upload_seite"))

    if not datei.filename.lower().endswith(".csv"):
        flash("Bitte eine .csv-Datei hochladen", "error")
        return redirect(url_for("import_csv.import_upload_seite"))

    zeilen = csv_parsen(datei.read())
    if not zeilen:
        flash("Keine verwertbaren Zeilen in der CSV gefunden - Format prüfen", "error")
        return redirect(url_for("import_csv.import_upload_seite"))

    upload_id = uuid4().hex[:12]
    tmp_pfad = _tmp_dir() / f"{upload_id}.json"
    with open(tmp_pfad, "w", encoding="utf-8") as f:
        json.dump(zeilen, f, ensure_ascii=False)

    return redirect(url_for("import_csv.import_vorschau", upload_id=upload_id))


@bp.route("/import/vorschau/<upload_id>")
def import_vorschau(upload_id):
    tmp_pfad = _tmp_dir() / f"{upload_id}.json"
    if not tmp_pfad.exists():
        flash("Import-Vorschau abgelaufen - bitte CSV erneut hochladen", "error")
        return redirect(url_for("import_csv.import_upload_seite"))

    with open(tmp_pfad, "r", encoding="utf-8") as f:
        zeilen = json.load(f)

    with open_db() as db:
        alle_behaelter = sorted(db["behaelter"].values(), key=lambda b: b.get("name", "").lower())
        standort_map = db["standorte"]

    return render_template(
        "import_vorschau.html",
        zeilen=list(enumerate(zeilen)),
        upload_id=upload_id,
        alle_behaelter=alle_behaelter,
        standort_map=standort_map,
    )


@bp.route("/import/bestaetigen", methods=["POST"])
def import_bestaetigen():
    upload_id = request.form.get("upload_id", "")
    tmp_pfad = _tmp_dir() / f"{upload_id}.json"
    if not tmp_pfad.exists():
        flash("Import-Vorschau abgelaufen - bitte CSV erneut hochladen", "error")
        return redirect(url_for("import_csv.import_upload_seite"))

    with open(tmp_pfad, "r", encoding="utf-8") as f:
        zeilen = json.load(f)

    uebernommen = 0
    with open_db() as db:
        for idx, zeile in enumerate(zeilen):
            if request.form.get(f"uebernehmen_{idx}") != "on":
                continue

            behaelter_id = request.form.get(f"behaelter_{idx}", "")
            if behaelter_id not in db["behaelter"]:
                continue  # ohne gültigen Behälter keine Übernahme dieser Zeile

            name = request.form.get(f"name_{idx}", zeile.get("name", "")).strip()
            if not name:
                continue

            try:
                menge = max(1, int(request.form.get(f"menge_{idx}", zeile.get("menge", 1))))
            except (TypeError, ValueError):
                menge = 1

            jetzt = datetime.now().isoformat()
            iid = neue_id()
            db["items"][iid] = {
                "id": iid,
                "name": name,
                "kategorie": request.form.get(f"kategorie_{idx}", zeile.get("kategorie_vorschlag", "")).strip(),
                "behaelter_id": behaelter_id,
                "gridfinity_zelle": "",
                "menge": menge,
                "einheit": "Stk",
                "groesse": request.form.get(f"variante_{idx}", zeile.get("variante", "")).strip(),
                "notizen": "",
                "foto": None,
                "aliexpress_link": zeile.get("link", ""),
                "erstellt": jetzt,
                "aktualisiert": jetzt,
            }
            uebernommen += 1

    tmp_pfad.unlink(missing_ok=True)

    flash(f"{uebernommen} Item(s) importiert", "success")
    return redirect(url_for("inventar_liste"))
