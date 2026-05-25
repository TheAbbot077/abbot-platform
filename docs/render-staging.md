# Render Staging Deployment

This project is staged on Render as three services:

- Django API: `abbot-study-api-staging`
- Celery worker: `abbot-study-celery-staging`
- Celery beat scheduler: `abbot-study-celery-beat-staging`
- Next.js frontend: `abbot-study-staging`

The API uses Render PostgreSQL through `DATABASE_URL` and Render Redis through `REDIS_URL`.
Uploaded textbooks use a Render disk mounted at `/var/data/media` for staging.

## Backend API

Build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

Start command:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

Health check:

```text
/api/health/
```

## Celery Worker

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
celery -A config worker --loglevel=info
```

## Celery Beat

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
celery -A config beat --loglevel=info
```

## Frontend

Build command:

```bash
npm ci && npm run build
```

Start command:

```bash
npm run start -- -p $PORT
```

## Required Staging Environment Variables

Backend:

- `DJANGO_SETTINGS_MODULE=config.settings_production`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_MEDIA_ROOT`
- `DATABASE_URL`
- `REDIS_URL`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_TUTOR_MODEL`

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`

Do not commit real API keys, database URLs, Redis URLs, or Django secrets.
