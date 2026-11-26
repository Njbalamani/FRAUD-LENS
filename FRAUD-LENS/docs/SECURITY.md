# FraudLens Security and Safety

## Operating mode

FraudLens defaults to synthetic mode. `FRAUDLENS_ENABLE_LIVE_DATA=false` is the safe default, and no live banking integration is included. Never enable live-data mode unless there is explicit legal authorization, a documented data-processing basis, and a reviewed production security design.

## Access control

- Admin users can manage users, organizations, and audit logs.
- Analyst users can run detection, investigate, close cases, and generate reports.
- Viewer users have read-only API access.
- Organization scoping is enforced in querysets and creation flows.
- Admin users may explicitly select another organization with `?organization=<id>`.

## Data protection

- Account numbers, counterparties, and device references are masked in API responses.
- Audit details are redacted for passwords, tokens, secrets, authorization values, account numbers, card numbers, IBANs, and device IDs.
- Binary report and evidence data is represented as byte-length summaries in audit details.
- CSRF protection is enabled for browser sessions.
- Rate limiting is applied through `FraudLensRateThrottle`.
- File uploads are size-limited by `FRAUDLENS_MAX_UPLOAD_MB`.

## CSV safety

Imports validate required headers, positive amounts, parseable timestamps, and allowed statuses. Invalid rows are retained as error summaries rather than silently discarded. Duplicate transaction IDs within an organization are skipped and counted.

## Production hardening

- Set a strong `FRAUDLENS_SECRET_KEY`.
- Set `FRAUDLENS_DEBUG=false` and configure `FRAUDLENS_ALLOWED_HOSTS`.
- Use PostgreSQL with TLS and managed backups.
- Terminate TLS at a trusted proxy and configure `SECURE_PROXY_SSL_HEADER`.
- Run Celery workers with least-privilege credentials.
- Store generated models and reports in controlled storage.
- Review model drift, false positives, and false negatives on a fixed schedule.

## Prohibited uses

- Automatic account freezing, transaction blocking, or fund holds
- Real-world accusations without human review and due process
- Unauthorized ingestion of personal or financial data
- Use as a sole basis for legal, employment, credit, or law-enforcement decisions
