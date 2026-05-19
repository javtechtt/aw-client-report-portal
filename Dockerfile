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

# Railway injects $PORT at runtime. Shell form (no JSON array) is required
# so the env var is expanded by the shell, not passed literally.
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 60 --log-file -
