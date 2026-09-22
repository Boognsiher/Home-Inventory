import os
import threading
import time
from datetime import datetime, timedelta
from io import BytesIO
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, send_file
from werkzeug.utils import secure_filename
import qrcode

import db as db_module
from config import Config
from db import open_db, neue_id

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

Config.ensure_dirs()


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def erlaubte_bilddatei(dateiname):
    return "." in dateiname and dateiname.rsplit(".", 1)[1].lower() in Config.ALLOWED_IMAGE_EXT


def foto_speichern(file_storage):
    """Speichert ein hochgeladenes Foto (verkleinert) im Upload-Verzeichnis und gibt den Dateinamen zurück."""
    if not file_storage or not file_storage.filename:
        return None
    if not erlaubte_bilddatei(file_storage.filename):
        return None

    from PIL import Image as PILImage

    endung = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    dateiname = f"{uuid4().hex[:16]}.{endung}"
    ziel_pfad = Config.UPLOAD_DIR / dateiname

    img = PILImage.open(file_storage.stream)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    max_size = 1600
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), PILImage.LANCZOS)
    img.save(ziel_pfad, quality=85, optimize=True)

    return dateiname


@app.template_filter("datum")
def format_datum(iso_str):
    if not iso_str:
        return "-"
    try:
        return datetime.fromisoformat(iso_str).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return iso_str


@app.context_processor
def globale_werte():
    return {"jahr": datetime.now().year}


@app.route("/uploads/<path:dateiname>")
def uploads(dateiname):
    return send_from_directory(Config.UPLOAD_DIR, dateiname)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    with open_db() as db:
        anzahl_standorte = len(db["standorte"])
        anzahl_behaelter = len(db["behaelter"])
        items = list(db["items"].values())
        anzahl_items = len(items)
        gesamtmenge = sum(i.get("menge", 0) for i in items)

        # Jinja kann keine Slices - deshalb hier schon begrenzen
        letzte_items = sorted(items, key=lambda i: i.get("aktualisiert", ""), reverse=True)[:5]

    return render_template(
        "dashboard.html",
        anzahl_standorte=anzahl_standorte,
        anzahl_behaelter=anzahl_behaelter,
        anzahl_items=anzahl_items,
        gesamtmenge=gesamtmenge,
        letzte_items=letzte_items,
    )


# ---------------------------------------------------------------------------
# Standorte
# ---------------------------------------------------------------------------

@app.route("/standorte")
def standorte_liste():
    with open_db() as db:
        standorte = sorted(db["standorte"].values(), key=lambda s: s.get("name", "").lower())
        behaelter_anzahl = {}
        for b in db["behaelter"].values():
            behaelter_anzahl[b["standort_id"]] = behaelter_anzahl.get(b["standort_id"], 0) + 1
    return render_template("standorte.html", standorte=standorte, behaelter_anzahl=behaelter_anzahl)


@app.route("/standorte/neu", methods=["POST"])
def standort_neu():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name darf nicht leer sein", "error")
        return redirect(url_for("standorte_liste"))

    with open_db() as db:
        sid = neue_id()
        db["standorte"][sid] = {
            "id": sid,
            "name": name,
            "beschreibung": request.form.get("beschreibung", "").strip(),
            "erstellt": datetime.now().isoformat(),
        }

    flash(f"Standort „{name}“ angelegt", "success")
    return redirect(url_for("standorte_liste"))


@app.route("/standorte/<sid>")
def standort_detail(sid):
    with open_db() as db:
        standort = db["standorte"].get(sid)
        if not standort:
            abort(404)
        behaelter = sorted(
            [b for b in db["behaelter"].values() if b["standort_id"] == sid],
            key=lambda b: b.get("name", "").lower(),
        )
        item_anzahl = {}
        for it in db["items"].values():
            item_anzahl[it["behaelter_id"]] = item_anzahl.get(it["behaelter_id"], 0) + 1

    return render_template("standort_detail.html", standort=standort, behaelter=behaelter, item_anzahl=item_anzahl)


@app.route("/standorte/<sid>/loeschen", methods=["POST"])
def standort_loeschen(sid):
    with open_db() as db:
        hat_behaelter = any(b["standort_id"] == sid for b in db["behaelter"].values())
        if hat_behaelter:
            flash("Standort enthält noch Behälter - erst diese verschieben oder löschen", "error")
            return redirect(url_for("standort_detail", sid=sid))
        db["standorte"].pop(sid, None)

    flash("Standort gelöscht", "success")
    return redirect(url_for("standorte_liste"))


# ---------------------------------------------------------------------------
# Behälter
# ---------------------------------------------------------------------------

@app.route("/behaelter/neu", methods=["POST"])
def behaelter_neu():
    name = request.form.get("name", "").strip()
    standort_id = request.form.get("standort_id", "")

    with open_db() as db:
        if not name or standort_id not in db["standorte"]:
            flash("Name und gültiger Standort erforderlich", "error")
            return redirect(request.referrer or url_for("standorte_liste"))

        bid = neue_id()
        db["behaelter"][bid] = {
            "id": bid,
            "name": name,
            "standort_id": standort_id,
            "beschreibung": request.form.get("beschreibung", "").strip(),
            "erstellt": datetime.now().isoformat(),
        }

    flash(f"Behälter „{name}“ angelegt", "success")
    return redirect(url_for("standort_detail", sid=standort_id))


@app.route("/behaelter/<bid>")
def behaelter_detail(bid):
    with open_db() as db:
        behaelter = db["behaelter"].get(bid)
        if not behaelter:
            abort(404)
        standort = db["standorte"].get(behaelter["standort_id"], {})
        items = sorted(
            [i for i in db["items"].values() if i["behaelter_id"] == bid],
            key=lambda i: i.get("name", "").lower(),
        )

    return render_template("behaelter_detail.html", behaelter=behaelter, standort=standort, items=items)


@app.route("/behaelter/<bid>/loeschen", methods=["POST"])
def behaelter_loeschen(bid):
    with open_db() as db:
        behaelter = db["behaelter"].get(bid)
        if not behaelter:
            abort(404)
        standort_id = behaelter["standort_id"]
        hat_items = any(i["behaelter_id"] == bid for i in db["items"].values())
        if hat_items:
            flash("Behälter enthält noch Items - erst diese verschieben oder löschen", "error")
            return redirect(url_for("behaelter_detail", bid=bid))
        db["behaelter"].pop(bid, None)

    flash("Behälter gelöscht", "success")
    return redirect(url_for("standort_detail", sid=standort_id))


@app.route("/behaelter/<bid>/qr.png")
def behaelter_qr(bid):
    with open_db() as db:
        if bid not in db["behaelter"]:
            abort(404)

    ziel_url = url_for("behaelter_detail", bid=bid, _external=True)
    img = qrcode.make(ziel_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ---------------------------------------------------------------------------
# Items / Inventar
# ---------------------------------------------------------------------------

@app.route("/inventar")
def inventar_liste():
    suche = request.args.get("q", "").strip().lower()

    with open_db() as db:
        items = list(db["items"].values())
        if suche:
            items = [
                i for i in items
                if suche in i.get("name", "").lower()
                or suche in i.get("kategorie", "").lower()
                or suche in i.get("notizen", "").lower()
            ]
        items.sort(key=lambda i: i.get("name", "").lower())

        behaelter_map = db["behaelter"]
        standort_map = db["standorte"]

    return render_template(
        "items_liste.html",
        items=items,
        suche=request.args.get("q", ""),
        behaelter_map=behaelter_map,
        standort_map=standort_map,
    )


@app.route("/items/<iid>")
def item_detail(iid):
    with open_db() as db:
        item = db["items"].get(iid)
        if not item:
            abort(404)
        behaelter = db["behaelter"].get(item["behaelter_id"], {})
        standort = db["standorte"].get(behaelter.get("standort_id", ""), {})

    return render_template("item_detail.html", item=item, behaelter=behaelter, standort=standort)


@app.route("/items/neu", methods=["GET", "POST"])
def item_neu():
    with open_db() as db:
        alle_behaelter = sorted(db["behaelter"].values(), key=lambda b: b.get("name", "").lower())
        standort_map = db["standorte"]

    vorausgewaehlter_behaelter = request.args.get("behaelter_id", "")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        behaelter_id = request.form.get("behaelter_id", "")

        with open_db() as db:
            if not name or behaelter_id not in db["behaelter"]:
                flash("Name und gültiger Behälter erforderlich", "error")
                return redirect(url_for("item_neu", behaelter_id=behaelter_id))

            dateiname = foto_speichern(request.files.get("foto"))

            iid = neue_id()
            jetzt = datetime.now().isoformat()
            db["items"][iid] = {
                "id": iid,
                "name": name,
                "kategorie": request.form.get("kategorie", "").strip(),
                "behaelter_id": behaelter_id,
                "gridfinity_zelle": request.form.get("gridfinity_zelle", "").strip(),
                "menge": max(0, int(request.form.get("menge") or 0)),
                "einheit": request.form.get("einheit", "Stk").strip() or "Stk",
                "groesse": request.form.get("groesse", "").strip(),
                "notizen": request.form.get("notizen", "").strip(),
                "foto": dateiname,
                "aliexpress_link": request.form.get("aliexpress_link", "").strip(),
                "erstellt": jetzt,
                "aktualisiert": jetzt,
            }

        flash(f"Item „{name}“ angelegt", "success")
        return redirect(url_for("item_detail", iid=iid))

    return render_template(
        "item_form.html",
        item=None,
        alle_behaelter=alle_behaelter,
        standort_map=standort_map,
        vorausgewaehlter_behaelter=vorausgewaehlter_behaelter,
    )


@app.route("/items/<iid>/bearbeiten", methods=["GET", "POST"])
def item_bearbeiten(iid):
    with open_db() as db:
        item = db["items"].get(iid)
        if not item:
            abort(404)
        alle_behaelter = sorted(db["behaelter"].values(), key=lambda b: b.get("name", "").lower())
        standort_map = db["standorte"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        behaelter_id = request.form.get("behaelter_id", "")

        with open_db() as db:
            item = db["items"].get(iid)
            if not item:
                abort(404)
            if not name or behaelter_id not in db["behaelter"]:
                flash("Name und gültiger Behälter erforderlich", "error")
                return redirect(url_for("item_bearbeiten", iid=iid))

            neues_foto = foto_speichern(request.files.get("foto"))
            if neues_foto:
                item["foto"] = neues_foto

            item.update({
                "name": name,
                "kategorie": request.form.get("kategorie", "").strip(),
                "behaelter_id": behaelter_id,
                "gridfinity_zelle": request.form.get("gridfinity_zelle", "").strip(),
                "menge": max(0, int(request.form.get("menge") or 0)),
                "einheit": request.form.get("einheit", "Stk").strip() or "Stk",
                "groesse": request.form.get("groesse", "").strip(),
                "notizen": request.form.get("notizen", "").strip(),
                "aliexpress_link": request.form.get("aliexpress_link", "").strip(),
                "aktualisiert": datetime.now().isoformat(),
            })
            db["items"][iid] = item

        flash(f"Item „{name}“ aktualisiert", "success")
        return redirect(url_for("item_detail", iid=iid))

    return render_template(
        "item_form.html",
        item=item,
        alle_behaelter=alle_behaelter,
        standort_map=standort_map,
        vorausgewaehlter_behaelter=item["behaelter_id"],
    )


@app.route("/items/<iid>/loeschen", methods=["POST"])
def item_loeschen(iid):
    with open_db() as db:
        item = db["items"].pop(iid, None)
        if not item:
            abort(404)
        behaelter_id = item["behaelter_id"]

    flash("Item gelöscht", "success")
    return redirect(url_for("behaelter_detail", bid=behaelter_id))


# ---------------------------------------------------------------------------
# Blueprints registrieren
# ---------------------------------------------------------------------------

from routes_ausbuchen import bp as ausbuchen_bp
from routes_import import bp as import_bp
from routes_verwaltung import bp as verwaltung_bp

app.register_blueprint(ausbuchen_bp)
app.register_blueprint(import_bp)
app.register_blueprint(verwaltung_bp)


# ---------------------------------------------------------------------------
# Automatisches nächtliches Backup (nur wenn sich das Inventar geändert hat)
# ---------------------------------------------------------------------------

def _backup_scheduler():
    while True:
        jetzt = datetime.now()
        naechste_pruefung = jetzt.replace(hour=Config.BACKUP_STUNDE, minute=0, second=0, microsecond=0)
        if naechste_pruefung <= jetzt:
            naechste_pruefung += timedelta(days=1)
        time.sleep(max(60, (naechste_pruefung - jetzt).total_seconds()))
        try:
            db_module.create_backup()
        except Exception as exc:
            app.logger.error(f"Automatisches Backup fehlgeschlagen: {exc}")


def backup_scheduler_starten():
    thread = threading.Thread(target=_backup_scheduler, daemon=True)
    thread.start()


if os.environ.get("DISABLE_BACKUP_SCHEDULER") != "1":
    # Läuft sowohl beim direkten Start als auch unter gunicorn (Docker),
    # wo __main__ nicht ausgeführt wird. In Tests via DISABLE_BACKUP_SCHEDULER
    # abgeschaltet, damit kein Hintergrund-Thread hängen bleibt.
    backup_scheduler_starten()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
