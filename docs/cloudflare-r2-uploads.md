# Cloudflare R2 Direct Uploads

Large PDFs should upload directly from the browser to Cloudflare R2. Django issues a short-lived presigned URL, the browser uploads the file to R2, and Django stores the resulting object key on the `Document`.

## Required Environment Variables

Backend API and Celery worker:

```text
CLOUDFLARE_R2_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_BUCKET_NAME=
CLOUDFLARE_R2_PUBLIC_BASE_URL=
DIRECT_UPLOAD_MAX_SIZE_BYTES=262144000
```

`CLOUDFLARE_R2_PUBLIC_BASE_URL` is optional for now, but keep it configured if the bucket later needs public/CDN object access.

## R2 Bucket CORS

Configure CORS on the R2 bucket so the frontend can upload directly:

```json
[
  {
    "AllowedOrigins": ["https://abbot-study-staging.onrender.com"],
    "AllowedMethods": ["PUT", "GET", "HEAD"],
    "AllowedHeaders": ["Content-Type"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

For production, replace the origin with the production frontend URL.

## Upload Flow

1. Frontend calls `POST /api/documents/direct-upload-url/`.
2. Django validates filename and file size.
3. Django returns a short-lived R2 presigned `PUT` URL.
4. Browser uploads the PDF directly to R2.
5. Frontend calls `POST /api/documents/complete-direct-upload/`.
6. Django creates the `Document` row with `storage_backend="r2"` and queues Celery.
7. Celery downloads the object to a temporary file, extracts ordered chapters, and deletes the temp file.

## Memory Notes

R2 removes the large upload from the Render web/frontend proxy path. It does not remove all PDF processing memory pressure. The staging Celery worker runs with:

```bash
--concurrency=1 --prefetch-multiplier=1 --max-tasks-per-child=10
```

This keeps large PDF processing from multiplying across worker processes on small Render instances.
