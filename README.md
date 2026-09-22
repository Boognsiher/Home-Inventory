# Werkstatt Inventar

Selbst gehostetes Werkstatt-Inventarsystem auf Basis von Flask, mit KI-gestützter Foto-Suche und Checkout. Läuft auf einem Raspberry Pi 3B im Heimnetz.

## Features

- 📦 Hierarchische Struktur: Standort → Behälter (QR-Code) → optional Gridfinity-Unterkategorie → Item
- 🤖 Visuelle Suche & Checkout: Foto aufnehmen, Claude Haiku identifiziert das Teil, Abgleich mit dem Inventar, direktes Ausbuchen
- 🛒 AliExpress-CSV-Import mit Vorschau/Bearbeiten und automatischer Kategorievorschlag
- 📤 Export als JSON, XLSX und ZIP-Vollbackup
- 💾 Automatisches nächtliches USB-Backup (nur bei Änderungen), letzte 30 Backups
- 📱 Mobile-first UI, optimiert für Chrome auf Android

## Stack

- Python / Flask, Jinja2-Templates
- JSON-Datenhaltung (`load_db` / `save_db`)
- Anthropic API (`claude-haiku-4-5`) für Bildidentifikation
- Pillow, qrcode, openpyxl

## Setup

```bash
git clone <repo-url>
cd werkstatt-inventar
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Umgebungsvariable für den Anthropic API Key setzen (z. B. in einer `.env`-Datei, siehe `.env.example`):

```
ANTHROPIC_API_KEY=sk-...
```

App starten:

```bash
python app.py
```

Standardmäßig erreichbar unter `http://localhost:5000`.

## Deployment (Raspberry Pi)

Läuft produktiv als systemd-Service auf einem Raspberry Pi 3B (`werkstatt.local`, Port 5000). Deployment erfolgt per SCP von Windows aus. Details siehe [`CLAUDE.md`](./CLAUDE.md).

## Bekannte Einschränkungen

- Kamerazugriff (`getUserMedia`) ist auf dem Samsung Browser unzuverlässig
- Chrome benötigt für lokales HTTP das Flag `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
- Workaround: native Kamera-App nutzen, Foto aus der Galerie hochladen

## Roadmap

- ESP32-CAM-Scanner (Phase 2)
- Verfeinerung der CSV-Spaltenzuordnung für regionale AliExpress-Varianten

## Lizenz

Privates Projekt — keine Lizenz für Fremdnutzung vorgesehen (bei Bedarf anpassen).
