# Changelog

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
