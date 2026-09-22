"""Export (JSON/XLSX/ZIP-Backup) und die Settings-Seite unter /einstellungen."""

from datetime import datetime
from io import BytesIO

from flask import Blueprint, render_template, send_file, flash, redirect, url_for, abort
from openpyxl import Workbook

import db as db_module
from config import Config
from db import open_db, liste_backups

bp = Blueprint("verwaltung", __name__)


@bp.route("/einstellungen")
def einstellungen():
    with open_db() as db:
        anzahl_standorte = len(db["standorte"])
        anzahl_behaelter = len(db["behaelter"])
        anzahl_items = len(db["items"])
        letztes_backup = db["meta"].get("letztes_backup")
        aenderung_seit_backup = db_module.backup_noetig()

    backups = liste_backups()
    backups_info = [
        {"name": p.name, "groesse_kb": round(p.stat().st_size / 1024, 1), "erstellt": datetime.fromtimestamp(p.stat().st_mtime)}
        for p in backups
    ]

    return render_template(
        "einstellungen.html",
        anzahl_standorte=anzahl_standorte,
        anzahl_behaelter=anzahl_behaelter,
        anzahl_items=anzahl_items,
        letztes_backup=letztes_backup,
        aenderung_seit_backup=aenderung_seit_backup,
        api_key_gesetzt=bool(Config.ANTHROPIC_API_KEY),
        backups=backups_info,
        backup_stunde=Config.BACKUP_STUNDE,
        backup_keep=Config.BACKUP_KEEP,
        data_dir=str(Config.DATA_DIR),
    )


@bp.route("/backup/erstellen", methods=["POST"])
def backup_erstellen():
    ziel = db_module.create_backup(force=True)
    if ziel:
        flash(f"Backup „{ziel.name}“ erstellt", "success")
    else:
        flash("Backup konnte nicht erstellt werden", "error")
    return redirect(url_for("verwaltung.einstellungen"))


@bp.route("/backup/<dateiname>")
def backup_herunterladen(dateiname):
    gueltige_namen = {p.name for p in liste_backups()}
    if dateiname not in gueltige_namen:
        abort(404)
    return send_file(Config.BACKUP_DIR / dateiname, as_attachment=True, download_name=dateiname)


@bp.route("/export/json")
def export_json():
    return send_file(Config.DB_PATH, as_attachment=True, download_name="inventory.json", mimetype="application/json")


@bp.route("/export/xlsx")
def export_xlsx():
    with open_db() as db:
        standorte = db["standorte"]
        behaelter = db["behaelter"]
        items = list(db["items"].values())

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventar"
    ws.append(["Name", "Kategorie", "Menge", "Einheit", "Größe", "Gridfinity-Zelle",
               "Behälter", "Standort", "Notizen", "AliExpress-Link", "Erstellt", "Aktualisiert"])

    for it in sorted(items, key=lambda i: i.get("name", "").lower()):
        b = behaelter.get(it.get("behaelter_id", ""), {})
        s = standorte.get(b.get("standort_id", ""), {})
        ws.append([
            it.get("name", ""),
            it.get("kategorie", ""),
            it.get("menge", 0),
            it.get("einheit", "Stk"),
            it.get("groesse", ""),
            it.get("gridfinity_zelle", ""),
            b.get("name", ""),
            s.get("name", ""),
            it.get("notizen", ""),
            it.get("aliexpress_link", ""),
            it.get("erstellt", ""),
            it.get("aktualisiert", ""),
        ])

    for spalte in ws.columns:
        breite = max((len(str(zelle.value)) for zelle in spalte if zelle.value), default=10)
        ws.column_dimensions[spalte[0].column_letter].width = min(40, breite + 2)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    dateiname = f"inventar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=dateiname,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
