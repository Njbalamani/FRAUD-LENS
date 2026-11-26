# FraudLens Deployment Guide

## Production checklist

1. Set `FRAUDLENS_DEBUG=false`.
2. Generate a long random `FRAUDLENS_SECRET_KEY`.
3. Set `FRAUDLENS_ALLOWED_HOSTS` to the exact public hostnames.
4. Keep `FRAUDLENS_MODE=synthetic` unless a separately reviewed live-data program is authorized.
5. Keep `FRAUDLENS_ENABLE_LIVE_DATA=false` for this repository.
6. Use PostgreSQL through `FRAUDLENS_DB_ENGINE=django.db.backends.postgresql`.
7. Terminate TLS at a trusted reverse proxy and forward `X-Forwarded-Proto`.
8. Run `python manage.py migrate --noinput` on each release.
9. Run `python manage.py collectstatic --noinput` on each release.
10. Run `python manage.py check` and `python manage.py test --verbosity 1` before release.
11. Confirm the proxy forwards `X-Forwarded-Proto` and the app emits HSTS, nosniff, and same-origin referrer/opener headers.
12. Run at least one Celery worker if asynchronous detection tasks are enabled.
13. Run Celery beat to rebuild nightly behavior baselines and run scheduled detection.
14. Monitor `/health/` for `status: ok` and `checks.database: ok`.

## Docker deployment

```bash
docker compose up --build -d
docker compose exec web python manage.py generate_synthetic_dataset
docker compose exec web python manage.py seed_demo
```

The compose stack includes PostgreSQL, Redis, the gunicorn web service, a Celery worker, and Celery beat. Beat schedules behavior-profile rebuilds at 01:45 and detection at 02:15 server local time.

## Operational guidance

- Risk scores are advisory and must never automatically freeze or block accounts.
- Review false positives and false negatives on a fixed cadence.
- Archive generated reports according to the organization's retention policy.
- Restrict admin access and review audit logs through `/api/core/audit-logs/`.
- Rotate API tokens and credentials on a fixed schedule.
- Keep uploaded CSV files inside the configured size limit.
- Retrain or re-evaluate models when transaction patterns materially change.

## Backup and recovery

Back up the PostgreSQL database, uploaded evidence, and generated model artifacts. Restore verification should include:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 1
python manage.py shell -c "from django.test import Client; print(Client().get('/health/').status_code)"
```
