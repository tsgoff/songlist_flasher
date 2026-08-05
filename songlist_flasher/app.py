#!/usr/bin/env python3
"""
Kleine Ingress-Webseite: Setlist-Excel hochladen, parse_setlist.py patcht die
ESPHome-YAML, danach kompiliert/flasht `esphome run` per OTA auf das Display.
Läuft als Foreground-Prozess im Add-on-Container (s6 service).
"""
import os
import shutil
import signal
import sys
import subprocess
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, request, render_template, Response, jsonify, stream_with_context

CONFIG_DIR = Path(os.environ.get("SONGLIST_CONFIG_DIR", "/data/esphome-config"))
DEVICE_IP = os.environ.get("SONGLIST_DEVICE_IP", "")
YAML_NAME = "esp32-matrix-portal-s3.yaml"
PARSER = CONFIG_DIR / "parse_setlist.py"
# Die vom Nutzer bearbeitbare Quelle im ESPHome-Verzeichnis von Home Assistant.
# Wird vor JEDEM Build nach CONFIG_DIR kopiert -- nur so wirkt eine Änderung im
# ESPHome-Editor sofort und nicht erst nach einem Add-on-Neustart.
SOURCE_YAML = Path(os.environ.get(
    "SONGLIST_SOURCE_YAML", f"/homeassistant/esphome/{YAML_NAME}"))
# Für die Anzeige in der Weboberfläche: /homeassistant ist der Mountpunkt im
# Container, im Dateieditor von Home Assistant heisst derselbe Pfad /config.
SOURCE_YAML_LABEL = str(SOURCE_YAML).replace("/homeassistant/", "/config/", 1)

app = Flask(__name__)

# Nur EIN Build zur Zeit: `esphome run` arbeitet immer im selben
# Build-Verzeichnis (.esphome/build/<node>). Zwei parallele Läufe löschen sich
# gegenseitig Dateien weg -- das endet in kaputten ninja-Dateien, fehlendem
# src/main.cpp und sehr verwirrenden CMake-Fehlern.
jobs = {}
jobs_lock = threading.Lock()
current_job_id = None
MAX_KEPT_JOBS = 5


def run_job(job_id, upload_path, clean_first):
    global current_job_id
    job = jobs[job_id]

    def emit(line):
        job["lines"].append(line)
        print(line, flush=True)

    keep_path = None
    try:
        yaml_path = CONFIG_DIR / YAML_NAME

        # Immer frisch aus der Nutzerdatei holen, damit im ESPHome-Editor
        # geänderte Farben/Schriftgrößen in diesen Build eingehen. Gebaut wird
        # weiterhin in CONFIG_DIR, nicht neben der Quelle -- sonst teilt sich der
        # Flasher das .esphome-Build-Verzeichnis mit dem ESPHome-Add-on.
        emit(f"Quelle: {SOURCE_YAML_LABEL}")
        if not SOURCE_YAML.is_file():
            emit(f"FEHLER: {SOURCE_YAML_LABEL} existiert nicht. "
                 "Add-on neu starten -- dann wird die Datei aus der Vorlage angelegt.")
            job["done"] = True
            job["ok"] = False
            return
        shutil.copyfile(SOURCE_YAML, yaml_path)

        emit(f"Parse Setlist: {upload_path.name}")
        result = subprocess.run(
            [sys.executable, str(PARSER), str(upload_path), str(yaml_path)],
            capture_output=True, text=True, cwd=str(CONFIG_DIR),
        )
        for line in (result.stdout + result.stderr).splitlines():
            emit(line)
        if result.returncode != 0:
            job["done"] = True
            job["ok"] = False
            return

        # Für einen künftigen Add-on-Neustart merken, damit die Setlist nicht
        # verloren geht, wenn dabei die YAML-Vorlage aktualisiert wird.
        for old in CONFIG_DIR.glob("last_setlist.*"):
            old.unlink(missing_ok=True)
        keep_path = CONFIG_DIR / f"last_setlist{upload_path.suffix}"
        upload_path.rename(keep_path)

        if not DEVICE_IP:
            emit("FEHLER: Keine Geräte-IP konfiguriert (Add-on Konfigurations-Tab).")
            job["done"] = True
            job["ok"] = False
            return

        def run_esphome(args, what):
            emit(what)
            # Eigene Prozessgruppe, damit /cancel auch die von esphome
            # gestarteten platformio-/ninja-Kinder mitnimmt.
            proc = subprocess.Popen(
                ["esphome"] + args, cwd=str(CONFIG_DIR), start_new_session=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            job["proc"] = proc
            for line in proc.stdout:
                emit(line.rstrip())
            proc.wait()
            job["proc"] = None
            return proc.returncode

        # YAML vorab prüfen: seit die Datei im ESPHome-Editor bearbeitet wird,
        # ist ein Einrückungs- oder Schema-Fehler der wahrscheinlichste Fehler --
        # und der kostet sonst erst nach Minuten Kompilieren eine Fehlermeldung.
        # Ausgabe nur im Fehlerfall: `esphome config` dumpt sonst die komplette
        # aufgelöste Konfiguration und würde den Log-Stream zumüllen.
        # Grenze: C++-Lambdas prüft das nicht, ein falsches Color(...) fällt
        # weiterhin erst beim Kompilieren auf.
        emit("Prüfe YAML ...")
        check = subprocess.run(["esphome", "config", YAML_NAME],
                               capture_output=True, text=True, cwd=str(CONFIG_DIR))
        if check.returncode != 0:
            for line in (check.stdout + check.stderr).splitlines():
                emit(line)
            emit(f"FEHLER: {SOURCE_YAML_LABEL} ist fehlerhaft -- im ESPHome-Add-on korrigieren.")
            job["done"] = True
            job["ok"] = False
            return

        # Rettungsanker, wenn ein abgebrochener Build kaputte Zwischenstände
        # hinterlassen hat (fehlendes src/, abgeschnittene ninja-Dateien).
        # Kostet einen kompletten Neubau, daher nur auf Wunsch.
        if clean_first and run_esphome(["clean", YAML_NAME], "Leere Build-Verzeichnis ...") != 0:
            emit("FEHLER: Build-Verzeichnis konnte nicht geleert werden.")
            job["done"] = True
            job["ok"] = False
            return

        rc = run_esphome(["run", "--device", DEVICE_IP, "--no-logs", YAML_NAME],
                         f"Kompiliere & flashe nach {DEVICE_IP} ...")
        if job.get("cancelled"):
            emit("Abgebrochen.")
        job["done"] = True
        job["ok"] = rc == 0 and not job.get("cancelled")
    except Exception as exc:
        emit(f"FEHLER: {exc}")
        job["done"] = True
        job["ok"] = False
    finally:
        if keep_path is None:
            upload_path.unlink(missing_ok=True)
        with jobs_lock:
            if current_job_id == job_id:
                current_job_id = None


@app.route("/")
def index():
    return render_template("index.html", device_ip=DEVICE_IP,
                           source_yaml=SOURCE_YAML_LABEL)


@app.route("/cancel", methods=["POST"])
def cancel():
    """Ohne das blockiert ein hängender Lauf das Add-on dauerhaft: der OTA-Upload
    kann minutenlang stehenbleiben, und solange gibt /upload nur noch 409."""
    with jobs_lock:
        job = jobs.get(current_job_id) if current_job_id else None
    if job is None:
        return jsonify({"error": "Es läuft kein Build."}), 409

    job["cancelled"] = True
    proc = job.get("proc")
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError) as exc:
            return jsonify({"error": f"Abbruch fehlgeschlagen: {exc}"}), 500
    return jsonify({"ok": True})


@app.route("/current")
def current():
    """Erlaubt dem Browser, sich nach einem Reload wieder anzuhängen -- ein
    Build läuft leicht 20 Minuten, da ist der Tab schnell mal geschlossen."""
    with jobs_lock:
        return jsonify({"job": current_job_id})


@app.route("/upload", methods=["POST"])
def upload():
    global current_job_id
    file = request.files.get("setlist")
    if not file or not file.filename:
        return jsonify({"error": "Keine Datei ausgewählt."}), 400
    ext = file.filename.lower().rsplit(".", 1)[-1]
    if ext not in ("xlsx", "csv"):
        return jsonify({"error": "Nur .xlsx oder .csv erlaubt."}), 400

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with jobs_lock:
        if current_job_id is not None:
            return jsonify({
                "error": "Es läuft bereits ein Build -- bitte abwarten.",
                "job": current_job_id,
            }), 409

        job_id = uuid.uuid4().hex
        upload_path = CONFIG_DIR / f"upload_{job_id}.{ext}"
        file.save(upload_path)

        for old_id in [j for j, s in jobs.items() if s["done"]][:-MAX_KEPT_JOBS]:
            del jobs[old_id]
        jobs[job_id] = {"lines": [], "done": False, "ok": None}
        current_job_id = job_id

    clean_first = request.form.get("clean") == "1"
    threading.Thread(target=run_job, args=(job_id, upload_path, clean_first),
                     daemon=True).start()
    return jsonify({"job": job_id})


@app.route("/stream/<job_id>")
def stream(job_id):
    def gen():
        sent = 0
        job = jobs.get(job_id)
        if job is None:
            yield "event: error\ndata: unbekannter Job\n\n"
            return
        while True:
            lines = job["lines"]
            while sent < len(lines):
                yield f"data: {lines[sent]}\n\n"
                sent += 1
            if job["done"]:
                yield f"event: done\ndata: {'ok' if job['ok'] else 'fail'}\n\n"
                break
            time.sleep(0.3)

    return Response(stream_with_context(gen()), mimetype="text/event-stream")


if __name__ == "__main__":
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=8099)
