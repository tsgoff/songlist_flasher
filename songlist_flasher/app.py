#!/usr/bin/env python3
"""
Kleine Ingress-Webseite: Setlist-Excel hochladen, parse_setlist.py patcht die
ESPHome-YAML, danach kompiliert/flasht `esphome run` per OTA auf das Display.
Läuft als Foreground-Prozess im Add-on-Container (s6 service).
"""
import os
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

app = Flask(__name__)
jobs = {}


def run_job(job_id, upload_path):
    job = jobs[job_id]

    def emit(line):
        job["lines"].append(line)

    try:
        yaml_path = CONFIG_DIR / YAML_NAME
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

        if not DEVICE_IP:
            emit("FEHLER: Keine Geräte-IP konfiguriert (Add-on Konfigurations-Tab).")
            job["done"] = True
            job["ok"] = False
            return

        emit(f"Kompiliere & flashe nach {DEVICE_IP} ...")
        proc = subprocess.Popen(
            ["esphome", "run", "--device", DEVICE_IP, "--no-logs", YAML_NAME],
            cwd=str(CONFIG_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            emit(line.rstrip())
        proc.wait()
        job["done"] = True
        job["ok"] = proc.returncode == 0
    except Exception as exc:
        emit(f"FEHLER: {exc}")
        job["done"] = True
        job["ok"] = False
    finally:
        upload_path.unlink(missing_ok=True)


@app.route("/")
def index():
    return render_template("index.html", device_ip=DEVICE_IP)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("setlist")
    if not file or not file.filename:
        return jsonify({"error": "Keine Datei ausgewählt."}), 400
    ext = file.filename.lower().rsplit(".", 1)[-1]
    if ext not in ("xlsx", "csv"):
        return jsonify({"error": "Nur .xlsx oder .csv erlaubt."}), 400

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    upload_path = CONFIG_DIR / f"upload_{job_id}.{ext}"
    file.save(upload_path)

    jobs[job_id] = {"lines": [], "done": False, "ok": None}
    threading.Thread(target=run_job, args=(job_id, upload_path), daemon=True).start()
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
