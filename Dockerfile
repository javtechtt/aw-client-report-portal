# Railway build for the AW Client Report Portal.
#
# Switched off Nixpacks because Nixpacks' Python provider doesn't reliably
# install apt packages, and WeasyPrint needs GTK runtime libs (pango,
# cairo, gdk-pixbuf, glib) loaded at process start or PDF generation
# raises "cannot load library 'libgobject-2.0-0'".
#
# Railway auto-detects the Dockerfile and prefers it over Nixpacks.

FROM python:3.11-slim

# WeasyPrint native deps + a base font set so PDFs render real glyphs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so the layer can be cached across code-only edits.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT at runtime. Explicit `sh -c` exec form guarantees:
#   1. The shell expands ${PORT:-8000} (avoids literal $PORT being passed
#      to gunicorn, which would error with "'$PORT' is not a valid port").
#   2. `exec` replaces the shell with gunicorn as PID 1 so SIGTERM
#      reaches gunicorn directly during shutdown.
#   3. PORT has a sensible default for non-Railway test runs.
#
# If Railway's UI has a Custom Start Command set, it overrides this CMD
# entirely — clear that field in Railway → Settings → Deploy if so.
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 60 --log-file -"]
