ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         python3 python3-venv python3-pip git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir esphome flask
ENV PATH="/opt/venv/bin:${PATH}"
ENV PLATFORMIO_CORE_DIR="/data/platformio"

WORKDIR /app
COPY app.py parse_setlist.py esp32-matrix-portal-s3.yaml /app/
COPY templates/ /app/templates/
COPY rootfs/ /

RUN chmod a+x /etc/services.d/songlist_flasher/run
