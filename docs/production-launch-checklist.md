# Production Deployment And Beta Launch Checklist

Use this checklist before opening Abbot Study to beta users.

## Production Environment Separation

- Create separate Render services for production.
- Use a separate production PostgreSQL database.
- Use a separate production Redis instance.
- Use separate media storage or a production Render disk.
- Do not reuse staging secrets, staging API keys, staging databases, or staging Redis URLs.

Required backend variables:

- `DJANGO_SETTINGS_MODULE=config.settings_production`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_MEDIA_ROOT`
- `DATABASE_URL`
- `REDIS_URL`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_TUTOR_MODEL`

Required frontend variables:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_BETA_FEEDBACK_URL`

## Security Settings

- Confirm `DEBUG=False`.
- Confirm HTTPS is enabled for frontend and backend.
- Confirm `SESSION_COOKIE_SECURE=True`.
- Confirm `CSRF_COOKIE_SECURE=True`.
- Confirm `SESSION_COOKIE_HTTPONLY=True`.
- Confirm `SESSION_COOKIE_SAMESITE=Lax` or stricter.
- Confirm HTTPS redirects are handled once. On Render, prefer the platform HTTPS edge redirect. Keep `DJANGO_SECURE_SSL_REDIRECT=False` unless a full request/response redirect test proves Django redirects are safe behind the proxy.
- Confirm HSTS settings are enabled after HTTPS is verified.
- Confirm `ALLOWED_HOSTS` contains only production backend hosts.
- Confirm `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` contain only production frontend origins.

## Admin Account

Create the first admin manually from a secure shell:

```bash
python manage.py createsuperuser
```

Rules:

- Use a unique admin email.
- Use a strong password stored in a password manager.
- Do not share admin credentials.
- Create normal test users separately.
- Disable or rotate any temporary launch admin accounts.

## Error Logging

- Confirm Render logs are visible for web, worker, and beat services.
- Confirm Django logs security warnings and request errors.
- Run a harmless 404 and verify it appears in platform logs if expected.
- Decide whether to add Sentry or another error tracker before wider beta.

## Backups

- Enable automated PostgreSQL backups.
- Document backup retention period.
- Test restoring a backup into a non-production database.
- Decide how uploaded textbook files are backed up.
- Record who owns backup monitoring.

## Privacy And Terms

- Confirm `/privacy` is linked from the landing page.
- Confirm `/terms` is linked from the landing page.
- Replace beta placeholder language with reviewed legal text before public production launch.
- Confirm signup copy explains optional demographic fields.

## Beta Feedback

- Configure `NEXT_PUBLIC_BETA_FEEDBACK_URL`.
- Open `/beta-feedback`.
- Submit a test feedback entry.
- Confirm the product team receives it.
- Link the feedback page from beta invite emails and onboarding messages.

## Beta User Invite Flow

- Prepare an invite list.
- Send invites in small batches.
- Include:
  - frontend URL
  - short beta expectations
  - privacy and terms links
  - feedback link
  - support/contact instructions
- Ask each beta user to test:
  - signup
  - subject creation
  - PDF upload
  - one lesson with The Abbot
  - one MCQ attempt
  - Ariel if unlocked
- Monitor logs and support messages after each batch.

## Launch Gate

Do not invite beta users until:

- Production deploy succeeds.
- Health check passes.
- Admin login works.
- Normal user signup/login/logout works.
- Mobile landing, signup, dashboard, and lesson flow pass QA.
- A sample PDF processes successfully.
- The Abbot can teach a concept.
- MCQ pass/fail updates progress.
- Normal users are blocked from admin routes.
