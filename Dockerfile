FROM python:3.12-slim

WORKDIR /app

# System-Abhängigkeiten für Pillow (Bildverarbeitung)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistente Daten liegen unter /app/data (siehe docker-compose.yml Volume)
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data/uploads /app/data/backups

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
