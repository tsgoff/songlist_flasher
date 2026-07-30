# Changelog

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
