# Render Staging Deployment

This project is staged on Render as three services:

- Django API: `abbot-study-api-staging`
- Celery worker: `abbot-study-celery-staging`
- Celery beat scheduler: `abbot-study-celery-beat-staging`
- Next.js frontend: `abbot-study-staging`

The API uses Render PostgreSQL through `DATABASE_URL` and Render Redis through `REDIS_URL`.
Uploaded textbooks use a Render disk mounted at `/var/data/media` for staging.
Render already serves HTTPS at the edge, so staging keeps Django's internal
`DJANGO_SECURE_SSL_REDIRECT=False` to avoid proxy redirect loops.

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
- `SESSION_COOKIE_SAMESITE=None`
- `CSRF_COOKIE_SAMESITE=None`
- `DATABASE_URL`
- `REDIS_URL`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_TUTOR_MODEL`

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`
- `API_PROXY_TARGET`
- `NEXT_PUBLIC_API_PROXY_TARGET`

Do not commit real API keys, database URLs, Redis URLs, or Django secrets.

## Login Redirects Back To Login

If a user logs in successfully but lands back on `/login`, check the browser network tab for `/api/auth/me/`.
If it returns `401`, the browser is probably not sending the Django session cookie.
If the network tab shows repeated `301` or `308` responses, check that:

- backend `DJANGO_SECURE_SSL_REDIRECT=False` on Render staging
- frontend `API_PROXY_TARGET` has only the backend origin, not `/api`
- frontend `NEXT_PUBLIC_API_BASE_URL=/api`

For Render frontend/API deployments, prefer same-origin browser requests through the Next.js proxy:

```text
NEXT_PUBLIC_API_BASE_URL=/api
API_PROXY_TARGET=https://abbot-study-api-staging.onrender.com
NEXT_PUBLIC_API_PROXY_TARGET=https://abbot-study-api-staging.onrender.com
```

This is especially important on mobile browsers, where cross-origin cookies are more aggressively restricted.

The backend also supports direct cross-origin session cookies when needed. In that case, set:

```text
SESSION_COOKIE_SAMESITE=None
CSRF_COOKIE_SAMESITE=None
```

These must be paired with HTTPS and secure cookies, which `config.settings_production` enables.
