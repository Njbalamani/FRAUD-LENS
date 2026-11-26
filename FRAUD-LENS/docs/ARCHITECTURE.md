# FraudLens Architecture

FraudLens is a modular Django monolith with clear domain boundaries and Celery-ready asynchronous work.

## Layers

- Presentation: Django templates, Chart.js, GSAP, and Three.js
- API: Django REST Framework viewsets, serializers, permissions, throttling, and token auth
- Domain: transaction, detection, behavior, graph, investigation, and report services
- Data: PostgreSQL-ready Django ORM with SQLite default for local demonstration
- Background: Celery tasks for detection runs and future scheduled jobs
- Storage: local static files and local model artifacts; production deployments can replace these with object storage

## Request flow

1. The browser requests a dashboard page or API endpoint.
2. Authentication and organization scoping resolve the active organization.
3. Query parameters constrain the dataset window and filters.
4. Domain services read ORM records, compute signals, and return serializable results.
5. Core middleware injects audit context, and model signals write redacted audit logs.
6. Responses mask sensitive identifiers before rendering.

## Detection pipeline

1. Transactions are ordered chronologically and converted into numeric features.
2. Rules score unusual amount, velocity, new counterparty, new device, off-hours behavior, and unusual location.
3. Isolation Forest produces an unsupervised anomaly signal.
4. When enough labeled examples exist, XGBoost or Random Forest produces a supervised probability.
5. Rule, model, and anomaly signals are combined into a 0-100 risk score.
6. Findings and risk scores are persisted with evidence and feature contributions.
7. Model performance metrics are stored for review in reports and explainability endpoints.

## Graph pipeline

1. Transactions become directed relationships between accounts and counterparties.
2. NetworkX computes layout, connected components, degree, and hub identifiers.
3. Clusters are ranked by size, edge count, value, and average risk.
4. The Three.js view renders masked labels and animated links.

## Safety boundaries

- Synthetic mode is the default and does not connect to external financial systems.
- Live-data configuration is deliberately opt-in and must be paired with legal authorization.
- Risk scores never trigger automatic account freezes, transaction blocks, or enforcement actions.
- All audit details are redacted before persistence.
