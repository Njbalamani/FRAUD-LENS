# FraudLens API

Base URL: `/api/`

All endpoints except `/api/`, `/api/schema/`, `/health/`, and `/api/accounts/token/` require authentication. Use session authentication in the browser or token authentication for scripts. Supply tokens as `Authorization: Token <token>`.

## Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/accounts/token/` | Obtain an API token |
| GET | `/api/accounts/me/` | Current authenticated user |
| GET | `/api/accounts/users/` | Admin-only user list |
| GET | `/api/accounts/organizations/` | Admin-only organization list |

## Core

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/` | API root and endpoint index |
| GET | `/api/schema/` | Lightweight OpenAPI-style endpoint index |
| GET | `/health/` | Service health and operational counters |
| GET | `/api/search/?q=<term>` | Cross-entity search |
| GET | `/api/core/audit-logs/` | Admin-only audit log list |

## Transactions

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/transactions/accounts/` | Masked financial accounts |
| GET | `/api/transactions/transactions/` | Masked transaction ledger |
| GET | `/api/transactions/summary/` | Aggregated transaction summary |
| POST | `/api/transactions/import/` | Multipart CSV import |
| GET | `/api/transactions/imports/` | Import history and validation errors |

CSV upload fields:

- `file`: CSV file, maximum size controlled by `FRAUDLENS_MAX_UPLOAD_MB`
- `column_mapping`: optional JSON object mapping canonical fields to CSV headers

Required canonical columns: `transaction_id`, `account_number`, `counterparty_reference`, `amount`, `timestamp`. Optional columns include `account_holder`, `currency`, `transaction_type`, `channel`, `location`, `device_reference`, `status`, `description`, and `is_fraud_label`.

## Detection

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/detection/analyze/` | Run detection and risk scoring |
| GET | `/api/detection/explain/` | Global feature importance, metrics, and limitations |
| GET | `/api/detection/explain/?transaction=<id>` | Transaction-level explanation |
| GET | `/api/detection/findings/` | Fraud findings |
| GET | `/api/detection/risk-scores/` | Transaction risk scores |
| GET | `/api/detection/runs/` | Detection run history |
| GET | `/api/detection/performance/` | Model performance history |

`POST /api/detection/analyze/` accepts `force` and optional `days`. It creates a detection run, findings, risk scores, and, when labeled data is sufficient, a `ModelPerformance` record.

## Behavior

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/behavior/profiles/` | Account baseline profiles |
| POST | `/api/behavior/rebuild/` | Rebuild profiles from observed transactions |
| GET | `/api/behavior/anomalies/` | Transactions deviating from behavioral baselines |

## Graph

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/graph/graph/` | Graph nodes, edges, positions, and stats |
| GET | `/api/graph/clusters/` | Connected-component clusters and hubs |
| GET | `/api/graph/path/?source=<id>&target=<id>` | Shortest path between identifiers |
| POST | `/api/graph/sync/` | Rebuild relationship records |
| GET | `/api/graph/relationships/` | Stored account-to-counterparty relationships |

## Investigations

| Method | Endpoint | Description |
| --- | --- | --- |
| GET/POST | `/api/investigations/cases/` | List or create cases |
| POST | `/api/investigations/cases/from-findings/` | Create a case from selected finding IDs |
| POST | `/api/investigations/cases/{id}/assign/` | Assign and set status |
| POST | `/api/investigations/cases/{id}/close/` | Close with mandatory resolution notes |
| GET/POST | `/api/investigations/notes/` | Case notes |
| GET/POST | `/api/investigations/evidence/` | Case evidence |

## Reports

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/reports/reports/` | Generated reports |
| POST | `/api/reports/generate/` | Generate `pdf`, `csv`, or `json` report |
| GET | `/api/reports/download/{id}/` | Download report bytes |

## Organization scoping

Authenticated users see their own organization only. Admin users may pass `?organization=<id>` on read endpoints and creation endpoints to operate on another organization. Raw account numbers, counterparties, and device identifiers are masked in API responses.
