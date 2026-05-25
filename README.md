# Abbot Study

Abbot Study is an AI-powered study management system. Students upload textbooks or notes, the backend extracts chapters and concepts in explicit sequence order, and the frontend guides learning through The Abbot, Ariel, MCQs, progress tracking, and reinforcement.

## Tech Stack

- Backend: Django, Django REST Framework, PostgreSQL, pgvector, Redis, Celery
- Frontend: Next.js, TypeScript, Tailwind CSS
- Deployment target: Render

## Local Setup

Copy the example environment files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Update `backend/.env` with your local database, Redis, and OpenAI values.

## Run With Docker

Start backend services:

```bash
docker compose up --build
```

The Django API runs at:

```text
http://localhost:8000/api
```

Run migrations:

```bash
docker compose exec backend python manage.py migrate
```

Create a local admin user:

```bash
docker compose exec backend python manage.py createsuperuser
```

## Frontend

From the frontend folder:

```bash
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:3000
```

For hosted deployments, the frontend should use the built-in API proxy:

```text
NEXT_PUBLIC_API_BASE_URL=/api
API_PROXY_TARGET=https://your-backend-service.example.com
```

This keeps browser API calls same-origin, which is more reliable on mobile browsers.

## Celery And Redis

Docker Compose starts:

- Redis
- Celery worker
- Celery beat

Celery uses `REDIS_URL`.

## Testing

Backend:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
```

Frontend:

```bash
cd frontend
npm run typecheck
```

## Staging And Production

Render staging is configured in:

- `render.yaml`
- `docs/render-staging.md`
- `docs/staging-qa-checklist.md`

Production launch planning is documented in:

- `docs/production-launch-checklist.md`
- `docs/beta-user-invite-flow.md`

Do not commit real `.env` files, API keys, database URLs, Redis URLs, or Django secrets.
