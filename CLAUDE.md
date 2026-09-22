# CLAUDE.md

Diese Datei gibt Claude Code Kontext, wenn im Repo gearbeitet wird.

## Projektüberblick

**Werkstatt Inventar** ist ein selbst gehostetes System zur Verwaltung physischer Werkstatt-Teile und -Komponenten, mit KI-gestützter Foto-Suche und Checkout. Läuft dauerhaft auf einem Raspberry Pi 3B im Heimnetz.

- Hierarchische Struktur: **Standort → Behälter (mit QR-Code) → optional Gridfinity-Unterkategorie → Item**
- Mobile-first Bedienung, primär über Chrome auf Android im lokalen WLAN

## Tech-Stack

- **Backend:** Python / Flask mit Jinja2-Templates
- **Datenhaltung:** JSON-Datei via `load_db` / `save_db` Pattern (keine SQL-DB)
- **Frontend:** Mobile-first HTML/CSS, kein Frontend-Framework
- **KI:** Anthropic API, Modell `claude-haiku-4-5` für Bildidentifikation (Visual Search / Checkout)
- **Libraries:** Pillow (Bildverarbeitung), qrcode (QR-Code-Erzeugung), openpyxl (Excel-Export)

## Architektur / Kernfunktionen

- **AliExpress-CSV-Import:** zweistufiger Flow (Upload → Vorschau/Bearbeiten → Bestätigen), flexibles CSV-Parsing, automatische Kategorievorschläge, manuelle Behälterzuordnung pro Item
- **Visuelle Suche & Checkout ("Ausbuchen"):** Foto aufnehmen → Claude Haiku identifiziert das Teil → Abgleich mit Live-Inventar → direktes Ausbuchen der Menge; mobil-optimierte 3-Schritt-UI
- **Export & Backup:** JSON-, XLSX- und ZIP-Vollbackup; nächtliches USB-Backup läuft nur an Tagen, an denen `inventory.json` verändert wurde; letzte 30 Backups werden aufbewahrt; Status auf der Settings-Seite sichtbar
- **Settings-Seite** unter `/einstellungen`

## Deployment

- Läuft auf Raspberry Pi 3B, IP `192.168.0.42`, Hostname `werkstatt.local` (via avahi-daemon), User `pi`
- Läuft als **systemd-Service** auf Port 5000
- Entwicklung erfolgt auf Windows (PowerShell); Deployment auf den Pi per **SCP**
- Netzwerkstabilität: Router-seitige DHCP-Reservierung + `.local`-Hostname wird gegenüber statischer IP-Konfiguration auf dem Pi bevorzugt

### Typischer Deployment-Ablauf
1. Änderungen lokal auf Windows entwickeln/testen
2. Dateien per SCP auf den Pi kopieren (SCP-Befehle laufen lokal, **nicht** in der SSH-Session)
3. Auf dem Pi: Service neu starten (`systemctl restart <service-name>`)

## Bekannte Eigenheiten

- Jinja2 unterstützt kein Python-Slice-Syntax (`|list[:5]`) — Listen müssen bereits in der Route geslict werden
- Kamerazugriff via `getUserMedia` ist auf dem Samsung Browser unzuverlässig
- Chrome benötigt für lokales HTTP das Flag `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
- Workaround fürs Scannen: native Kamera-App nutzen und aus der Galerie hochladen
- XLSX (via openpyxl) wird CSV vorgezogen, wegen besserer Excel-Kompatibilität

## Arbeitsweise / Konventionen

- Features werden bevorzugt als klar abgegrenzte Patches geliefert: neue Routen-Dateien + Templates, mit expliziten Integrationsschritten (wo im Code einfügen, welche SCP-Pfade, welcher Restart-Befehl)
- Manuelle Kontrolle wird Automatisierung vorgezogen, wo Nutzerurteil zählt (z. B. manuelle Behälterzuordnung statt Auto-Zuordnung beim Import)
- KI-Funktionen (Visual Search, Hybrid-Suche) sind Assistenzfunktionen — keine autonomen Entscheider
- Schritt-für-Schritt-Anleitungen für Terminal-/Deployment-Schritte sind erwünscht

## Geplant / Phase 2

- ESP32-CAM-Scanner (Pistolengriff, OLED-Display, Akku), Integration via HTTP POST an die Flask-App
- Ggf. Anpassung der AliExpress-Import-Spaltenzuordnung für regionale CSV-Varianten

## Hinweise für Claude Code

- Kein Test-Framework aktuell im Projekt — vor größeren Änderungen kurz nachfragen, ob Tests gewünscht sind
- Secrets (Anthropic API Key etc.) NICHT in Code oder Repo einchecken — über Umgebungsvariable / `.env` (siehe `.gitignore`) einlesen
- Beim Vorschlagen von Deployment-Schritten: PowerShell-Syntax für lokale Befehle, SSH/Bash-Syntax für Befehle auf dem Pi, und beides klar auseinanderhalten
