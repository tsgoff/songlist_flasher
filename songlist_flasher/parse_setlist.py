#!/usr/bin/env python3
"""
Liest eine Setlist (CSV oder XLSX) und patcht die initial_value-Felder
einer ESPHome-YAML mit Songtiteln + Übergangsanweisungen.

Neues XLSX-Format (eine Spalte, abwechselnd):
    Songtitel
    Einzeln auf Bühne
    <Titel 1>
    <Anweisung 1>
    <Titel 2>
    <Anweisung 2>
    ...
    <Titel n>            (letzter Titel darf ohne Anweisung enden)

Altes Format (zwei Spalten, nur Titel, keine Anweisungen):
    Nr.   Songtitel
    1     <Titel 1>
    2     <Titel 2>
    ...

CSV: gleiche Zweispalten-Logik wie das alte XLSX-Format (";"-getrennt).

Verwendung:
    parse_setlist.py <input.xlsx|csv> <config.yaml> [max_len] [chunks_per_list]
"""
import sys
import re
import csv
import io
import zipfile
from xml.etree import ElementTree as ET

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
TITLE_HEADER_WORDS = {"songtitel", "song", "title", "titel"}


def read_csv(path):
    with open(path, "rb") as f:
        data = f.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    text = data.decode("utf-8", errors="replace")
    titles = []
    reader = csv.reader(io.StringIO(text), delimiter=";")
    for i, row in enumerate(reader):
        if len(row) < 2:
            continue
        title = row[1].strip()
        if not title:
            continue
        if i == 0 and title.lower() in TITLE_HEADER_WORDS:
            continue
        if i == 0 and re.match(r"^\s*nr\.?\s*$", row[0], re.I):
            continue
        titles.append(title)
    return titles, []


def _xlsx_column_a_values(path):
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("s:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["s"])))
        sheets = sorted(
            n for n in z.namelist()
            if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
        )
        if not sheets:
            sys.exit("ERROR: kein Worksheet in XLSX gefunden")
        root = ET.fromstring(z.read(sheets[0]))

    def cell_text(c):
        t = c.get("t", "n")
        v = c.find("s:v", NS)
        is_n = c.find("s:is", NS)
        if t == "s" and v is not None:
            try:
                return shared[int(v.text)]
            except (ValueError, IndexError):
                return ""
        if t == "inlineStr" and is_n is not None:
            return "".join(x.text or "" for x in is_n.iter("{%s}t" % NS["s"]))
        if v is not None and v.text is not None:
            return v.text
        return ""

    rows = []
    for row in root.find("s:sheetData", NS).findall("s:row", NS):
        cells = {}
        for c in row.findall("s:c", NS):
            m = re.match(r"([A-Z]+)", c.get("r", "") or "")
            if m:
                cells[m.group(1)] = cell_text(c).strip()
        rows.append(cells)
    return rows


def read_xlsx(path):
    rows = _xlsx_column_a_values(path)

    # Altes Zweispalten-Format erkennen: Header "Songtitel" steht in Spalte B.
    for cells in rows:
        if cells.get("B", "").lower() in TITLE_HEADER_WORDS:
            titles = []
            first = True
            for cells in rows:
                col_b = cells.get("B", "")
                if not col_b:
                    continue
                if first:
                    first = False
                    if col_b.lower() in TITLE_HEADER_WORDS:
                        continue
                titles.append(col_b)
            return titles, []
        if cells.get("B", ""):
            break  # erste nicht-leere Zeile hat Inhalt in B, aber keinen Header -> kein altes Format

    # Neues Einspalten-Format: Werte in Spalte A, Header "Songtitel" markiert den Start.
    values = [cells.get("A", "") for cells in rows]
    start = None
    for i, v in enumerate(values):
        if v.lower() in TITLE_HEADER_WORDS:
            start = i + 1
            break
    if start is None:
        sys.exit("ERROR: konnte weder altes noch neues XLSX-Format erkennen "
                  "(kein 'Songtitel'-Header gefunden).")

    # Direkt nach dem "Songtitel"-Header kann ein zweiter Header ("Einzeln auf
    # Bühne" o.ä.) für die Anweisungsspalte stehen -- eine weitere nicht-leere
    # Zeile, bevor der erste echte Titel kommt. Wir überspringen genau eine
    # solche Zeile, falls vorhanden.
    if start < len(values) and values[start]:
        start += 1

    entries = [v for v in values[start:] if v]
    titles = entries[0::2]
    instructions = entries[1::2]
    if not titles:
        sys.exit("ERROR: keine Songtitel nach dem Header gefunden.")
    return titles, instructions


def chunk(items, max_len, max_chunks, label):
    chunks = [""] * max_chunks
    idx = 0
    for item in items:
        if len(item) > max_len:
            sys.exit(f"ERROR: Eintrag zu lang für ein Feld ({max_len} Zeichen): '{item}'")
        cand = chunks[idx] + ("|" if chunks[idx] else "") + item
        if len(cand) <= max_len:
            chunks[idx] = cand
            continue
        idx += 1
        if idx >= max_chunks:
            sys.exit(f"ERROR: {label} passt nicht in {max_chunks} x {max_len} Zeichen.")
        chunks[idx] = item
    return chunks


def yaml_escape(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def replace_initial_value(text, entity_id, new_value):
    pattern = re.compile(
        r"(id:\s*" + re.escape(entity_id) + r"\b)"
        r"(.*?)"
        r"(^([ \t]+)initial_value:\s*)"
        r"(.*?)(\r?\n)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        sys.exit(f"ERROR: konnte 'initial_value' für id '{entity_id}' nicht finden.")
    middle = m.group(2)
    if re.search(r"^\s*-\s*platform:|\bid:\s*\w+", middle, re.MULTILINE):
        sys.exit(f"ERROR: Block für id '{entity_id}' enthält fremde Direktiven.")
    replacement = m.group(1) + middle + m.group(3) + yaml_escape(new_value) + m.group(6)
    return text[: m.start()] + replacement + text[m.end():]


def main():
    if len(sys.argv) < 3:
        sys.exit(f"Verwendung: {sys.argv[0]} <input.xlsx|csv> <config.yaml> [max_len] [chunks_per_list]")

    input_path = sys.argv[1]
    yaml_path = sys.argv[2]
    max_len = int(sys.argv[3]) if len(sys.argv) > 3 else 255
    max_chunks = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    ext = input_path.lower().rsplit(".", 1)[-1]
    if ext == "csv":
        titles, instructions = read_csv(input_path)
    elif ext == "xlsx":
        titles, instructions = read_xlsx(input_path)
    else:
        sys.exit(f"ERROR: Format '.{ext}' nicht unterstützt (csv/xlsx).")

    if not titles:
        sys.exit("ERROR: Keine Songs gefunden.")

    title_chunks = chunk(titles, max_len, max_chunks, "Songliste")
    instr_chunks = chunk(instructions, max_len, max_chunks, "Anweisungsliste")

    print(f"  Songs:        {len(titles)}")
    print(f"  Anweisungen:  {len(instructions)}")
    for i, c in enumerate(title_chunks, 1):
        print(f"  song_list_{i}: {len(c)} Zeichen")
    for i, c in enumerate(instr_chunks, 1):
        print(f"  instr_list_{i}: {len(c)} Zeichen")

    with open(yaml_path, "r", encoding="utf-8") as f:
        yaml_text = f.read()

    for i, c in enumerate(title_chunks, 1):
        yaml_text = replace_initial_value(yaml_text, f"song_list_{i}", c)
    for i, c in enumerate(instr_chunks, 1):
        yaml_text = replace_initial_value(yaml_text, f"instr_list_{i}", c)

    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_text)

    print(f"  YAML aktualisiert: {yaml_path}")


if __name__ == "__main__":
    main()
