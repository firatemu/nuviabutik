# NuviaButik production image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_DISABLE_PIP_VERSION_CHECK=1     PIP_NO_CACHE_DIR=1

# System deps for psycopg2 + Pillow
RUN apt-get update && apt-get install -y --no-install-recommends       build-essential libpq-dev libjpeg-dev libpng-dev zlib1g-dev       libxml2-dev libxslt1-dev libffi-dev libpango-1.0-0 libpangoft2-1.0-0       && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . /app

# Create log/static dirs (settings.py expects these for build-time collectstatic)
RUN mkdir -p /srv/data/nuviabutik/logs /srv/data/nuviabutik/media /app/staticfiles

# Collect staticfiles at build time (sqlite-only, won't conflict)
ENV DJANGO_SETTINGS_MODULE=stoktakip.settings     DEBUG=False     SECRET_KEY=build-time-only-key-not-secret     DATABASE_URL=sqlite:///tmp/db.sqlite3     NUVIABUTIK_DATA_DIR=/srv/data/nuviabutik     ALLOWED_HOSTS=*     REDIS_URL=redis://127.0.0.1:6379/1
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Default command — runs migrations then gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn --config gunicorn.conf.py stoktakip.wsgi:application"]
