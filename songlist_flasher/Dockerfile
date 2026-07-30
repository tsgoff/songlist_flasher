ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         python3 python3-venv python3-pip git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# esphome gepinnt, damit ein stiller Downgrade auffällt: esphome >= 2026.7
# braucht Python >= 3.12. Auf dem alten bookworm-Image (Python 3.11) wählte pip
# deshalb ungefragt 2026.6.5 -- und dessen OTA-Client brach beim Flashen
# reproduzierbar mit "receiving chunk result response: timed out" ab, während
# das offizielle ESPHome-Add-on (2026.7.3) dasselbe Gerät über denselben Port in
# 3 Sekunden lud. Beim Hochziehen der Version also immer die Python-Version des
# Basis-Images mitprüfen (siehe build.yaml).
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir esphome==2026.7.3 flask
ENV PATH="/opt/venv/bin:${PATH}"
ENV PLATFORMIO_CORE_DIR="/data/platformio"

WORKDIR /app
COPY app.py parse_setlist.py esp32-matrix-portal-s3.yaml /app/
COPY templates/ /app/templates/
COPY rootfs/ /

RUN chmod a+x /etc/services.d/songlist_flasher/run
