"""Flexibles Parsing von AliExpress-CSV-Exporten.

Die Spaltennamen unterscheiden sich je nach Region/Exportwerkzeug
(z. B. "Product Name" vs. "Titel"), deshalb wird über Kandidatenlisten
gesucht statt feste Spaltenpositionen anzunehmen.
"""

import csv
import io
import re

SPALTEN_KANDIDATEN = {
    "name": ["product name", "produktname", "title", "titel", "name", "artikel", "item name"],
    "menge": ["quantity", "menge", "anzahl", "qty", "stück", "stueck"],
    "preis": ["price", "preis", "item price", "unit price", "gesamtpreis", "total", "total price"],
    "link": ["url", "link", "product url", "produktlink", "item url"],
    "variante": ["sku", "variante", "specification", "spezifikation", "option", "properties"],
}

KATEGORIE_SCHLUESSELWOERTER = {
    "Schrauben": ["schraube", "screw", "bolt", " m2", " m3", " m4", " m5", " m6", "gewindeschraube"],
    "Muttern": ["mutter", "nut", "nutsert"],
    "Kabel": ["kabel", "cable", "wire", "draht", "litze"],
    "Stecker": ["stecker", "connector", "buchse", "jst", "xt60", "xt30", "dupont", "molex"],
    "Elektronik": [
        "modul", "sensor", "chip", "platine", "pcb", "esp32", "esp8266", "arduino",
        "widerstand", "resistor", "kondensator", "capacitor", "relais", "relay", "ic ",
    ],
    "Werkzeug": ["werkzeug", "tool", "zange", "schraubendreher", "screwdriver", "pinzette", "lötkolben"],
    "3D-Druck": ["filament", "düse", "nozzle", "hotend", "bettoberfläche", "gridfinity"],
    "Lager": ["lager", "bearing", "kugellager"],
    "Motoren": ["motor", "servo", "stepper", "schrittmotor"],
}


def _finde_spalte(header, kandidaten):
    header_lower = [h.strip().lower() for h in header]
    for kandidat in kandidaten:
        if kandidat in header_lower:
            return header_lower.index(kandidat)
    return None


def kategorie_vorschlagen(name):
    name_lower = (name or "").lower()
    for kategorie, schluesselwoerter in KATEGORIE_SCHLUESSELWOERTER.items():
        if any(wort in name_lower for wort in schluesselwoerter):
            return kategorie
    return "Sonstiges"


def csv_parsen(datei_bytes):
    """Parst eine AliExpress-CSV-Exportdatei.

    Gibt eine Liste von Dicts zurück: name, menge, preis, link, variante,
    kategorie_vorschlag. Zeilen ohne erkennbaren Namen werden übersprungen.
    """
    text = datei_bytes.decode("utf-8-sig", errors="replace")

    try:
        dialekt = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialekt = csv.excel

    zeilen = list(csv.reader(io.StringIO(text), dialekt))
    if not zeilen:
        return []

    header = zeilen[0]
    idx_name = _finde_spalte(header, SPALTEN_KANDIDATEN["name"])
    idx_menge = _finde_spalte(header, SPALTEN_KANDIDATEN["menge"])
    idx_preis = _finde_spalte(header, SPALTEN_KANDIDATEN["preis"])
    idx_link = _finde_spalte(header, SPALTEN_KANDIDATEN["link"])
    idx_variante = _finde_spalte(header, SPALTEN_KANDIDATEN["variante"])

    def wert(zeile, idx):
        if idx is None or idx >= len(zeile):
            return ""
        return zeile[idx].strip()

    ergebnis = []
    for zeile in zeilen[1:]:
        if not any(z.strip() for z in zeile):
            continue

        name = wert(zeile, idx_name) if idx_name is not None else (zeile[0].strip() if zeile else "")
        if not name:
            continue

        menge_roh = wert(zeile, idx_menge) or "1"
        try:
            menge = int(float(menge_roh.replace(",", ".")))
        except ValueError:
            menge = 1

        preis_roh = wert(zeile, idx_preis)
        preis = None
        if preis_roh:
            try:
                preis = float(re.sub(r"[^0-9.,]", "", preis_roh).replace(",", "."))
            except ValueError:
                preis = None

        ergebnis.append({
            "name": name,
            "menge": max(1, menge),
            "preis": preis,
            "link": wert(zeile, idx_link),
            "variante": wert(zeile, idx_variante),
            "kategorie_vorschlag": kategorie_vorschlagen(name),
        })

    return ergebnis
