"""Visuelle Suche & Checkout ("Ausbuchen"): Foto -> Claude Haiku identifiziert
das Teil -> Abgleich mit Live-Inventar -> direktes Ausbuchen der Menge.

KI-Funktion ist reine Assistenz: die/der Nutzer:in bestätigt den Treffer und
die Menge manuell, es wird nichts automatisch ausgebucht.
"""

import base64
import json
import re
from datetime import datetime
from io import BytesIO

from flask import Blueprint, jsonify, render_template, request

from config import Config
from db import open_db

bp = Blueprint("ausbuchen", __name__)


@bp.route("/ausbuchen")
def ausbuchen_page():
    """Seite: Foto aufnehmen -> Teil finden -> ausbuchen"""
    return render_template("ausbuchen.html")


@bp.route("/api/visual-search", methods=["POST"])
def visual_search():
    """
    Foto hochladen -> Claude analysiert -> matched gegen Inventar.
    Gibt Top-Treffer mit Item-IDs zurück.
    """
    if "foto" not in request.files:
        return jsonify({"error": True, "message": "Kein Foto erhalten"}), 400

    foto = request.files["foto"]
    if not foto or foto.filename == "":
        return jsonify({"error": True, "message": "Leeres Foto"}), 400

    if not Config.ANTHROPIC_API_KEY:
        return jsonify({
            "error": True,
            "message": "Kein ANTHROPIC_API_KEY konfiguriert (siehe .env)",
        }), 500

    try:
        import anthropic
        from PIL import Image as PILImage

        img = PILImage.open(foto.stream)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        max_size = 1200
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), PILImage.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        img_b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

        with open_db() as db:
            items = list(db["items"].values())

        if not items:
            return jsonify({"treffer": [], "beschreibung": "Keine Items im Inventar"})

        inventar_liste = []
        for it in items:
            menge = it.get("menge", 0)
            if menge > 0:
                inventar_liste.append({
                    "id": it["id"],
                    "name": it.get("name", ""),
                    "kategorie": it.get("kategorie", ""),
                    "groesse": it.get("groesse", ""),
                    "notizen": it.get("notizen", ""),
                    "menge": menge,
                    "einheit": it.get("einheit", "Stk"),
                })

        inventar_json = json.dumps(inventar_liste, ensure_ascii=False)

        system_prompt = """Du bist ein Werkzeug-Erkennungssystem für eine Werkstatt-Inventar-App.
Analysiere das Foto und vergleiche es mit dem Inventar.
Antworte NUR mit einem JSON-Objekt, ohne Markdown-Backticks, ohne Erklärungen.

JSON-Format:
{
  "beschreibung": "Kurze Beschreibung was auf dem Foto zu sehen ist (1 Satz)",
  "erkanntes_objekt": "Name des erkannten Objekts",
  "treffer": [
    {
      "item_id": "die-id-aus-dem-inventar",
      "konfidenz": 0.95,
      "begruendung": "Kurze Begründung warum dieser Treffer"
    }
  ]
}

Regeln:
- Maximal 5 Treffer, sortiert nach Konfidenz (höchste zuerst)
- Nur Items aus dem Inventar verwenden (item_id muss exakt übereinstimmen)
- Konfidenz: 0.0 bis 1.0
- Wenn nichts passt: leeres treffer-Array"""

        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_b64,
                },
            },
            {
                "type": "text",
                "text": f"Inventar (nur Items mit Menge > 0):\n{inventar_json}\n\nAnalysiere das Foto und finde passende Items aus dem Inventar."
            }
        ]

        client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text.strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                return jsonify({"error": True, "message": "KI-Antwort konnte nicht geparst werden", "raw": raw}), 500

        treffer_angereichert = []
        with open_db() as db:
            for treffer in result.get("treffer", []):
                item_id = treffer.get("item_id")
                item = db["items"].get(item_id)
                if item:
                    behaelter = db["behaelter"].get(item.get("behaelter_id", ""), {})
                    standort = db["standorte"].get(behaelter.get("standort_id", ""), {})
                    treffer_angereichert.append({
                        "item_id": item_id,
                        "konfidenz": treffer.get("konfidenz", 0),
                        "begruendung": treffer.get("begruendung", ""),
                        "name": item.get("name", ""),
                        "kategorie": item.get("kategorie", ""),
                        "groesse": item.get("groesse", ""),
                        "menge": item.get("menge", 0),
                        "einheit": item.get("einheit", "Stk"),
                        "behaelter_name": behaelter.get("name", ""),
                        "standort_name": standort.get("name", ""),
                    })

        return jsonify({
            "beschreibung": result.get("beschreibung", ""),
            "erkanntes_objekt": result.get("erkanntes_objekt", ""),
            "treffer": treffer_angereichert,
        })

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Visual search error: {e}")
        return jsonify({"error": True, "message": str(e)}), 500


@bp.route("/api/items/<item_id>/ausbuchen", methods=["POST"])
def ausbuchen_item(item_id):
    """
    Menge um X reduzieren (Standard: 1).
    Body (JSON, optional): { "menge": 2 }
    """
    data = request.get_json(silent=True) or {}
    try:
        menge_ausbuchen = int(data.get("menge", 1))
    except (TypeError, ValueError):
        menge_ausbuchen = 1

    with open_db() as db:
        item = db["items"].get(item_id)
        if not item:
            return jsonify({"error": True, "message": "Item nicht gefunden"}), 404

        neue_menge = max(0, item.get("menge", 0) - menge_ausbuchen)
        item["menge"] = neue_menge
        item["aktualisiert"] = datetime.now().isoformat()
        db["items"][item_id] = item

        antwort = {
            "success": True,
            "item_id": item_id,
            "name": item.get("name"),
            "neue_menge": neue_menge,
            "einheit": item.get("einheit", "Stk"),
        }

    return jsonify(antwort)
