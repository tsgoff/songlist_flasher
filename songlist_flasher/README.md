# Songlist Flasher (Home Assistant Add-on)

Lokales HA-Add-on: Setlist-Excel hochladen -- kompiliert und flasht per OTA
automatisch das ESP32-Matrix-Display.

## Installation (als Add-on-Repository)

1. In Home Assistant: **Einstellungen → Add-ons → Add-on Store** → oben rechts
   die drei Punkte → **Repositories** → folgende URL einfügen:
   `https://github.com/tsgoff/songlist_flasher`
2. Nach dem Hinzufügen erscheint „Songlist Flasher" in der Add-on-Liste
   (Seite ggf. einmal neu laden). Add-on installieren (der erste Build lädt
   Debian-Pakete + ESPHome herunter, das dauert ein paar Minuten).
3. Im **Konfiguration**-Tab eintragen:
   - `wifi_ssid` / `wifi_password`: WLAN, mit dem das Display verbunden ist
   - `device_ip`: aktuelle IP-Adresse des Displays im Netzwerk
     (am Router nachsehen, idealerweise als feste/reservierte IP einrichten,
     damit sie sich nicht per DHCP ändert)
4. Add-on **starten**, dann über die Sidebar öffnen.
5. Excel-Datei auswählen → „Aktualisieren" klicken → Fortschritt im Log
   verfolgen. Bei Erfolg ist das Display direkt aktualisiert.

## Hinweis für Maintainer: Sync mit dem Haupt-Projekt

`esp32-matrix-portal-s3.yaml` und `parse_setlist.py` liegen hier als eigene
Kopien (Docker kann beim Bauen des Add-ons keine Dateien außerhalb dieses
Repos einbinden). Wenn sich die YAML oder der Parser im Haupt-Projekt
("songlist") ändern, müssen beide Dateien erneut in diesen Add-on-Ordner
kopiert werden, z. B.:

```bash
cp <pfad-zum-songlist-projekt>/esp32-matrix-portal-s3.yaml songlist_flasher/
cp <pfad-zum-songlist-projekt>/parse_setlist.py songlist_flasher/
```

Danach committen und pushen -- der Supervisor zieht Updates für lokale
Repository-Add-ons erst nach einem manuellen "Neu laden"/Update im Add-on
Store.

## Caveats

- Erster Kompiliervorgang lädt ESP-IDF/PlatformIO-Toolchains (~1-2 GB,
  braucht Internet); spätere Läufe nutzen den `/data`-Cache und sind
  schneller.
- `arch` ist auf `amd64`/`aarch64` begrenzt -- eine 32-Bit-HAOS-Installation
  (alter Raspberry Pi) wird nicht unterstützt.
- OTA läuft über die feste IP aus der Konfiguration, nicht über mDNS/`.local`
  -- robuster in einem Add-on-Container, erfordert aber eine stabile IP.
