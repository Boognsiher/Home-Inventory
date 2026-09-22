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

## Fernzugriff über das Internet (optional)

Standardmäßig ist die App nur im Heimnetz erreichbar und hat **kein Login** — das ist im
WLAN zuhause unkritisch. Für den Zugriff von unterwegs gibt es zwei Wege:

**Option A (empfohlen): VPN statt öffentlicher Freigabe** — z. B. [Tailscale](https://tailscale.com/)
oder der VPN-Server des NAS-Herstellers. Dann bleibt die App unverändert ohne Login,
da nur Geräte im VPN überhaupt an Port 5000 herankommen. Kein Portfreigabe, kein Zertifikat nötig.

**Option B: echte öffentliche Erreichbarkeit** — dafür bringt dieses Repo einen optionalen
[Caddy](https://caddyserver.com/)-Reverse-Proxy mit, der sich automatisch ein Let's-Encrypt-Zertifikat
holt, plus einen Passwortschutz in der App selbst (ohne Passwort wäre das Inventar für jeden im
Internet sichtbar und veränderbar, inklusive des kostenpflichtigen KI-Foto-Endpunkts).

### 1. DDNS-Hostnamen einrichten

Ein gekaufter Domainname ist **nicht nötig** — ein kostenloser DDNS-Hostname reicht, da Let's
Encrypt nur einen Hostnamen braucht (keine nackte IP):

- **NAS-eigenes DDNS** (Synology: *Systemsteuerung → Externer Zugriff → DDNS*, QNAP: *myQNAPcloud*)
  — ergibt z. B. `deinname.synology.me`. Meist die einfachste Variante.
  - **[DuckDNS](https://www.duckdns.org/)** — herstellerunabhängig, kostenlos, `deinname.duckdns.org`.

### 2. Router-Portfreigabe

Port **80** (nur für die Let's-Encrypt-Zertifikatsprüfung) und **443** (HTTPS) vom Router auf
die interne IP des NAS weiterleiten. Port 5000 muss **nicht** weitergeleitet werden — der bleibt
nur im Heimnetz erreichbar.

### 3. `.env` ergänzen

```
APP_PASSWORT=<sicheres Passwort, z. B. via `openssl rand -base64 18`>
PUBLIC_DOMAIN=deinname.duckdns.org
```

### 4. Mit Reverse-Proxy starten

```bash
docker compose --profile public up -d --build
```

Das startet zusätzlich zur App einen Caddy-Container, der `PUBLIC_DOMAIN` auf Port 443 mit
automatischem HTTPS-Zertifikat bedient und intern an die App weiterleitet. Danach ist die App
unter `https://deinname.duckdns.org` erreichbar (Login mit `APP_PASSWORT` erforderlich) —
und weiterhin auch im Heimnetz direkt unter `http://<NAS-IP>:5000` (dort ebenfalls mit Login,
sobald `APP_PASSWORT` gesetzt ist).

**Zurück zu reiner Heimnetz-Nutzung:** `docker compose --profile public down` (stoppt nur den
Caddy-Container) und `APP_PASSWORT` in der `.env` wieder leeren, um das Login abzuschalten.

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
