# Backend Django — pensado para Coolify (Base Directory: /, raíz del repo).
# Todo lo que hoy vive en variables de entorno (SECRET_KEY, DATABASE_URL,
# R2_*, BREVO_*, etc. — ver README.md y config/settings.py) se configura
# igual en Coolify, nunca se hornea en la imagen.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq5 alcanza para psycopg2-binary en runtime (ya trae su propio libpq
# empaquetado en el wheel, pero el paquete del sistema evita sorpresas).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Mismo comando que usaba Railway (Procfile/railway.json): migra, junta
# estáticos (los sirve whitenoise, no hace falta nginx aparte) y levanta
# gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3 --log-file -"]
