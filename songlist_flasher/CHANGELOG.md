# Changelog

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
