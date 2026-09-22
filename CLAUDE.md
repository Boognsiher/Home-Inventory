# CLAUDE.md

Diese Datei gibt Claude Code Kontext, wenn im Repo gearbeitet wird.

## Projektüberblick

**Werkstatt Inventar** ist ein selbst gehostetes System zur Verwaltung physischer Werkstatt-Teile und -Komponenten, mit KI-gestützter Foto-Suche und Checkout. Läuft dauerhaft als Docker-Container auf einem NAS im Heimnetz.

- Hierarchische Struktur: **Standort → Behälter (mit QR-Code) → optional Gridfinity-Unterkategorie → Item**
- Mobile-first Bedienung, primär über Chrome auf Android im lokalen WLAN

## Tech-Stack

- **Backend:** Python / Flask mit Jinja2-Templates, Produktivbetrieb über `gunicorn`
- **Datenhaltung:** JSON-Datei via `load_db` / `save_db` Pattern (keine SQL-DB) — siehe `db.py`
- **Frontend:** Mobile-first HTML/CSS, kein Frontend-Framework
- **KI:** Anthropic API, Modell `claude-haiku-4-5` für Bildidentifikation (Visual Search / Checkout)
- **Libraries:** Pillow (Bildverarbeitung), qrcode (QR-Code-Erzeugung), openpyxl (Excel-Export)
- **Container:** Docker + docker-compose, ein Volume (`DATA_DIR`) für alle persistenten Daten
- **Tests:** pytest (`tests/`), Basis-Abdeckung für DB-Layer und Kernrouten

## Dateistruktur

- `app.py` — App-Setup, Dashboard, Standorte/Behälter/Items-CRUD, QR-Code-Route, Backup-Scheduler-Start
- `config.py` — `Config`-Klasse, liest ausschließlich Umgebungsvariablen (siehe `.env.example`)
- `db.py` — `load_db`/`save_db`/`open_db`-Pattern, Backup-Erstellung & -Aufräumen
- `csv_import.py` — flexibles AliExpress-CSV-Parsing, Kategorievorschläge
- `routes_ausbuchen.py` — Blueprint: Visual Search + Ausbuchen
- `routes_import.py` — Blueprint: CSV-Import-Flow
- `routes_verwaltung.py` — Blueprint: Export (JSON/XLSX), Backup, `/einstellungen`
- `templates/`, `static/css/style.css` — Jinja2-Templates, mobile-first CSS
- `Caddyfile` + `caddy`-Service in `docker-compose.yml` (Profil `public`) — optionaler HTTPS-Reverse-Proxy für Internet-Zugriff, holt automatisch Let's-Encrypt-Zertifikat für `PUBLIC_DOMAIN`
- `tests/` — pytest, nutzt `DATA_DIR` in einem temporären Verzeichnis (siehe `tests/conftest.py`)

## Architektur / Kernfunktionen

- **AliExpress-CSV-Import:** zweistufiger Flow (Upload → Vorschau/Bearbeiten → Bestätigen), flexibles CSV-Parsing, automatische Kategorievorschläge, manuelle Behälterzuordnung pro Item
- **Visuelle Suche & Checkout ("Ausbuchen"):** Foto aufnehmen → Claude Haiku identifiziert das Teil → Abgleich mit Live-Inventar → direktes Ausbuchen der Menge; mobil-optimierte 3-Schritt-UI
- **Export & Backup:** JSON-, XLSX- und ZIP-Vollbackup; automatisches nächtliches Backup (In-App-Scheduler, kein Cron/USB nötig) läuft nur, wenn sich `inventory.json` seit dem letzten Backup inhaltlich geändert hat; letzte 30 Backups werden aufbewahrt; Status auf der Settings-Seite sichtbar
- **Settings-Seite** unter `/einstellungen`
- **Login/Passwortschutz:** deaktiviert per Default (reine Heimnetz-Nutzung); sobald `APP_PASSWORT` in `.env` gesetzt ist, verlangt `app.py`s globaler `before_request`-Hook einen Login (`/login`, Session-Cookie, siehe `Config.SESSION_TAGE`). Nur relevant, wenn die App öffentlich erreichbar gemacht wird.

## Deployment

- Läuft als **Docker-Container** (via `docker-compose.yml`) auf einem NAS im Heimnetz, Port 5000
- Alle persistenten Daten (`inventory.json`, Foto-Uploads, ZIP-Backups) liegen in einem einzigen gemounteten Verzeichnis (`DATA_DIR`, Standard `/app/data` im Container) — auf dem NAS als Bind-Mount auf einen Shared Folder
- Secrets/Konfiguration ausschließlich über `.env` (siehe `.env.example`), nie im Image oder Repo
- Entwicklung kann auf jedem Rechner mit Docker erfolgen; Deployment auf den NAS per `docker compose up -d --build` (lokal auf dem NAS oder via Docker-Kontext/Registry, je nach NAS-Fähigkeiten)
- Kein systemd/SCP-Workflow mehr nötig — `restart: unless-stopped` übernimmt den Neustart nach NAS-Reboot

### Typischer Deployment-Ablauf
1. Repo auf den NAS bringen (z. B. `git clone`/`git pull` direkt auf dem NAS, oder Datei-Sync)
2. `.env` aus `.env.example` erzeugen und `ANTHROPIC_API_KEY`/`SECRET_KEY` setzen
3. `docker compose up -d --build` auf dem NAS ausführen (SSH oder NAS-eigene Docker-UI wie Synology Container Manager/Portainer)
4. Bei Code-Änderungen: `docker compose up -d --build` erneut ausführen (Volume mit `data/` bleibt erhalten)

### HTTPS für Kamerazugriff (optional)
`getUserMedia` (Fotoaufnahme für Visual Search) verlangt im Browser einen sicheren Kontext. Im lokalen Netz per HTTP funktioniert weiterhin der Chrome-Flag-Workaround (siehe unten). Wer das vermeiden will: NAS-eigenen Reverse-Proxy (z. B. Synology "Anwendungsportal"/Reverse Proxy oder QNAP-Äquivalent) mit Let's-Encrypt- oder selbstsigniertem Zertifikat vor den Container schalten, der Container selbst bleibt HTTP-only auf Port 5000. Alternativ den mitgelieferten Caddy-Proxy nutzen (siehe unten), der das gleich mitbringt.

### Fernzugriff über das Internet (optional)
Zwei Wege, ausführlich in README.md beschrieben:
- **VPN (empfohlen für die meisten Fälle):** Tailscale oder NAS-eigener VPN-Server — App bleibt unverändert ohne Login, da nur VPN-Clients an Port 5000 kommen.
- **Echte öffentliche Erreichbarkeit:** `APP_PASSWORT` + `PUBLIC_DOMAIN` in `.env` setzen, DDNS-Hostname einrichten (kein gekaufter Domainname nötig, z. B. NAS-eigenes DDNS oder DuckDNS), Router-Ports 80+443 auf den NAS weiterleiten, dann `docker compose --profile public up -d --build` — startet zusätzlich den Caddy-Container, der automatisch ein Let's-Encrypt-Zertifikat für `PUBLIC_DOMAIN` holt und an die App weiterleitet. Ohne `--profile public` läuft alles wie bisher nur im Heimnetz.

## Bekannte Eigenheiten

- Jinja2 unterstützt kein Python-Slice-Syntax (`|list[:5]`) — Listen müssen bereits in der Route geslict werden
- Kamerazugriff via `getUserMedia` ist auf dem Samsung Browser unzuverlässig
- Chrome benötigt für lokales HTTP das Flag `chrome://flags/#unsafely-treat-insecure-origin-as-secure` (alternativ: HTTPS-Reverse-Proxy, siehe oben)
- Workaround fürs Scannen: native Kamera-App nutzen und aus der Galerie hochladen
- XLSX (via openpyxl) wird CSV vorgezogen, wegen besserer Excel-Kompatibilität
- `Config.DATA_DIR` wird beim Modul-Import ausgewertet — in Tests muss `DATA_DIR` (und `DISABLE_BACKUP_SCHEDULER=1`) **vor** dem Import von `config`/`app` gesetzt werden (siehe `tests/conftest.py`)

## Arbeitsweise / Konventionen

- Features werden bevorzugt als klar abgegrenzte Patches geliefert: neue Routen-Dateien/Blueprints + Templates, mit expliziten Integrationsschritten (wo registrieren, welcher `docker compose`-Befehl)
- Manuelle Kontrolle wird Automatisierung vorgezogen, wo Nutzerurteil zählt (z. B. manuelle Behälterzuordnung statt Auto-Zuordnung beim Import)
- KI-Funktionen (Visual Search, Hybrid-Suche) sind Assistenzfunktionen — keine autonomen Entscheider
- Schritt-für-Schritt-Anleitungen für Terminal-/Deployment-Schritte sind erwünscht (Bash/SSH-Syntax für NAS-Befehle)

## Geplant / Phase 2

- ESP32-CAM-Scanner (Pistolengriff, OLED-Display, Akku), Integration via HTTP POST an die Flask-App
- Ggf. Anpassung der AliExpress-Import-Spaltenzuordnung für regionale CSV-Varianten

## Hinweise für Claude Code

- pytest-Tests liegen unter `tests/` (`pytest -q` im Projektroot mit aktivierter venv) — bei neuen Routen/DB-Logik nach Möglichkeit mit abdecken
- Secrets (Anthropic API Key etc.) NICHT in Code oder Repo einchecken — über Umgebungsvariable / `.env` (siehe `.gitignore`) einlesen
- Beim Vorschlagen von Deployment-Schritten: Bash/SSH-Syntax für NAS-Befehle, klar kennzeichnen ob lokal oder auf dem NAS auszuführen
