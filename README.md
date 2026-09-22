# Werkstatt Inventar

Selbst gehostetes Werkstatt-Inventarsystem auf Basis von Flask, mit KI-gestützter Foto-Suche und Checkout. Läuft als Docker-Container auf einem NAS im Heimnetz.

## Features

- 📦 Hierarchische Struktur: Standort → Behälter (QR-Code) → optional Gridfinity-Unterkategorie → Item
- 🤖 Visuelle Suche & Checkout: Foto aufnehmen, Claude Haiku identifiziert das Teil, Abgleich mit dem Inventar, direktes Ausbuchen
- 🛒 AliExpress-CSV-Import mit Vorschau/Bearbeiten, automatischem Kategorievorschlag und manueller Behälterzuordnung
- 📤 Export als JSON, XLSX und ZIP-Vollbackup
- 💾 Automatisches nächtliches Backup (nur bei Änderungen), letzte 30 Backups
- 📱 Mobile-first UI, optimiert für Chrome auf Android

## Stack

- Python / Flask, Jinja2-Templates, gunicorn (Produktivbetrieb)
- JSON-Datenhaltung (`load_db` / `save_db`, siehe `db.py`)
- Anthropic API (`claude-haiku-4-5`) für Bildidentifikation
- Pillow, qrcode, openpyxl
- Docker / docker-compose für den Betrieb auf dem NAS
- pytest für Basis-Tests

## Setup auf dem NAS (Docker)

Voraussetzung: Docker + Docker Compose auf dem NAS verfügbar (z. B. Synology Container Manager, QNAP Container Station, TrueNAS Apps, oder klassisch per SSH).

```bash
git clone <repo-url> werkstatt-inventar
cd werkstatt-inventar
cp .env.example .env
```

`.env` bearbeiten und mindestens setzen:

```
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=<zufälliger Wert, z. B. via `openssl rand -hex 32`>
```

Container bauen und starten:

```bash
docker compose up -d --build
```

Die App ist danach unter `http://<NAS-IP>:5000` erreichbar. Alle persistenten Daten (`inventory.json`, Foto-Uploads, ZIP-Backups) liegen im gemounteten Ordner `./data` neben der `docker-compose.yml` — dieser sollte Teil der regulären NAS-Datensicherung sein.

**Update auf eine neue Version:**

```bash
git pull
docker compose up -d --build
```

## Setup für lokale Entwicklung (ohne Docker)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # ANTHROPIC_API_KEY und SECRET_KEY eintragen
python app.py
```

Standardmäßig erreichbar unter `http://localhost:5000`.

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

## Bekannte Einschränkungen

- Kamerazugriff (`getUserMedia`) ist auf dem Samsung Browser unzuverlässig
- Chrome benötigt für lokales HTTP das Flag `chrome://flags/#unsafely-treat-insecure-origin-as-secure` — alternativ einen HTTPS-Reverse-Proxy vor den Container schalten (z. B. über die NAS-eigene Reverse-Proxy-Funktion), siehe [`CLAUDE.md`](./CLAUDE.md)
- Workaround: native Kamera-App nutzen, Foto aus der Galerie hochladen

## Roadmap

- ESP32-CAM-Scanner (Phase 2)
- Verfeinerung der CSV-Spaltenzuordnung für regionale AliExpress-Varianten

## Lizenz

Privates Projekt — keine Lizenz für Fremdnutzung vorgesehen (bei Bedarf anpassen).
