# Changelog

## 1.1.0

- Die Geräte-YAML ist jetzt in Home Assistant bearbeitbar. Gebaut wird aus
  `/config/esphome/esp32-matrix-portal-s3.yaml` -- also aus der Datei, die im
  ESPHome-Add-on im Editor liegt. Farben, Schriftgrößen und kleinere Anpassungen
  gehen damit ohne Git. Bisher las der Flasher nur seine private Kopie unter
  `/data` und überschrieb die bei jedem Start; die Datei im ESPHome-Verzeichnis
  wurde nie angesehen, was zu zwei divergierenden Konfigurationen für dasselbe
  Gerät führte.
- Änderungen im Editor wirken beim nächsten Upload -- ein Add-on-Neustart ist
  nicht nötig. Gebaut wird weiterhin unter `/data`, damit sich der Flasher das
  `.esphome`-Build-Verzeichnis nicht mit dem offiziellen ESPHome-Add-on teilt.
- **Einmalige Migration beim ersten Start:** eine vorhandene
  `/config/esphome/esp32-matrix-portal-s3.yaml` wird als `.yaml.bak` gesichert
  (ein bereits vorhandenes Backup wird nie überschrieben), dann schreibt das
  Add-on die aktuelle Vorlage an ihre Stelle. Danach gehört die Datei euch und
  wird nicht mehr angefasst.
- **Achtung:** Add-on-Updates ändern die Gerätekonfiguration deshalb nicht mehr
  von allein. Die mitgelieferte Vorlage liegt zum Vergleichen als
  `esp32-matrix-portal-s3.template.yaml` daneben und wird bei jedem Start
  aktualisiert -- Neues daraus muss bewusst übernommen werden.
- WLAN-Zugangsdaten kommen aus `/config/esphome/secrets.yaml`, falls vorhanden;
  die Datei wird nur gelesen, nie geschrieben. Fehlende `wifi_ssid`/
  `wifi_password` werden aus den Add-on-Optionen ergänzt, und ohne eigene
  `secrets.yaml` bleibt es beim bisherigen Verhalten. Weitere `!secret`-Einträge
  im Editor brechen den Build damit nicht mehr.
- Vor dem Kompilieren läuft `esphome config`. Ein Einrückungs- oder Schema-Fehler
  im Editor kostet jetzt Sekunden statt eines abgebrochenen Builds nach Minuten.
  C++-Lambdas prüft das nicht -- ein falsches `Color(...)` fällt weiter erst beim
  Kompilieren auf.

## 1.0.9

- Songwechsel-Sperre von 1500ms auf 800ms -- direkt im ESPHome-Editor erprobt,
  weil 1,5s beim Weiterschalten zu träge war. Gilt jetzt für "weiter" und
  "zurück"; vorher entprellten die beiden unterschiedlich.

## 1.0.8

- Die regelmäßigen Resets im Auftritt sind weg: `api:` stand ohne Optionen da,
  und ESPHome rebootet dann per Default nach 15 Minuten ohne API-Client
  (`reboot_timeout: 15min`). Ohne Home Assistant in Reichweite lief der Timer
  jedes Mal voll ab -- alle 15 Minuten ein Neustart, den ganzen Abend. Der
  Fallback-Hotspot war unbeteiligt; die Weboberfläche auf Port 80 hält den Timer
  auch nicht auf. Jetzt `reboot_timeout: 0s` für `api:` und `wifi:`.
- Der zuletzt angezeigte Song überlebt Reset und Stromausfall: nach dem
  Einschalten wird wieder dort aufgeblättert, wo aufgehört wurde. Ist die neue
  Setlist kürzer als der gemerkte Index, startet die Anzeige bei Song 1.

## 1.0.7

- Zeilenversatz behoben: Die Zeile direkt unter "Songtitel" wurde immer als
  zweiter Header verworfen. Fehlt der (z.B. "Einzeln auf Bühne"), fiel der
  erste Songtitel weg -- danach standen alle Anweisungen in der Songzeile und
  umgekehrt. Übersprungen wird jetzt nur noch, was wirklich eine Überschrift
  ist. Die Leerzeile als Workaround stört nicht, ist aber nicht mehr nötig.

## 1.0.6

- Basis-Image auf Debian trixie (Python 3.13). 1.0.5 liess sich nicht bauen:
  bookworm liefert nur Python 3.11, esphome 2026.7.3 verlangt aber >= 3.12.

## 1.0.5

- OTA funktioniert wieder: esphome ist jetzt auf 2026.7.3 gepinnt. Vorher waehlte
  pip auf dem Python-3.11-Image stillschweigend das aeltere 2026.6.5, dessen
  OTA-Client das Display reproduzierbar mit "receiving chunk result response:
  timed out" nicht flashen konnte -- das offizielle ESPHome-Add-on (2026.7.3)
  lud dasselbe Geraet ueber denselben Port in 3 Sekunden.

## 1.0.4

- "Abbrechen"-Button: Ein hängender OTA-Upload blockierte das Add-on dauerhaft,
  weil jeder weitere Upload nur noch 409 bekam. Der Abbruch beendet die ganze
  Prozessgruppe (esphome samt platformio/ninja-Kindern).
- `power_save_mode: none` im WLAN-Block -- der schlafende WLAN-Stack verzögert
  zusammen mit der DMA-Last des HUB75-Panels die OTA-Bestätigungen.

## 1.0.3

- Es läuft nur noch EIN Build gleichzeitig. Ein zweiter Upload während eines
  laufenden Builds startete bisher `esphome run` erneut im selben
  Build-Verzeichnis -- beide Läufe löschten sich gegenseitig Dateien weg
  (fehlendes `src/main.cpp`, abgeschnittene ninja-Dateien, wirre CMake-Fehler).
  Ein zweiter Upload hängt sich jetzt an den laufenden Build an.
- Nach einem Reload (oder in einem zweiten Browser) wird der laufende Build
  wieder angezeigt, statt den Fortschritt zu verlieren.
- Neue Option "Build-Verzeichnis vorher leeren" (`esphome clean`), um einen
  kaputten Zwischenstand ohne Shell-Zugriff zu reparieren.

## 1.0.2

- Add-on startet wieder: Der Service brach beim Start still mit Exit-Code 2 ab,
  wenn noch keine Setlist hochgeladen war (Ingress zeigte "502 Bad Gateway").
  Ursache: `bashio` setzt `errexit`+`pipefail`, und `ls last_setlist.*` liefert
  Exit 2, wenn das Glob nicht matcht.
- Eine fehlerhafte gespeicherte Setlist verhindert den Start nicht mehr -- es
  wird dann mit der YAML-Vorlage gestartet und eine Warnung geloggt.

## 1.0.1

- Kompilierfehler behoben: `&id(...)` ergab `TemplateText**`, dadurch schlug
  `t->state` in den Lambdas für Song- und Anweisungsliste fehl.

## 1.0.0

- Erste Version: Setlist (XLSX/CSV) über Ingress hochladen, ESPHome-YAML
  patchen und per OTA auf das Matrix-Display flashen.
