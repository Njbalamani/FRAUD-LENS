# FraudLens ER Diagram

## Entity relationships

```text
Organization 1---* User
Organization 1---* FinancialAccount
Organization 1---* Transaction
Organization 1---* DetectionRun
Organization 1---* FraudFinding
Organization 1---* RiskScore
Organization 1---* AccountBehaviorProfile
Organization 1---* InvestigationCase
Organization 1---* Report
Organization 1---* AuditLog
Organization 1---* TransactionImport
Organization 1---* TransactionRelationship

FinancialAccount 1---* Transaction
FinancialAccount 1---1 AccountBehaviorProfile

Transaction 1---1 RiskScore
Transaction 1---* FraudFinding

DetectionRun 1---* FraudFinding
DetectionRun 1---* RiskScore

FraudFinding *---* InvestigationCase
InvestigationCase 1---* CaseNote
InvestigationCase 1---* CaseEvidence
```

## Key entities

| Entity | Purpose |
| --- | --- |
| Organization | Tenant boundary for all fraud and investigation records |
| User | Authentication principal with admin, analyst, or viewer role |
| FinancialAccount | Synthetic account record with masked API exposure |
| Transaction | Ledger event with amount, timestamp, channel, device, and location |
| TransactionImport | CSV validation and import audit trail |
| TransactionRelationship | Aggregated account-to-counterparty edge |
| DetectionRun | One execution of the detection pipeline |
| FraudFinding | Explainable rule or model signal attached to a transaction |
| RiskScore | Composite 0-100 score and feature contributions |
| ModelPerformance | Precision, recall, F1, ROC-AUC, and confusion matrix |
| AccountBehaviorProfile | Historical baseline for account behavior |
| InvestigationCase | Analyst workflow with status, priority, and resolution |
| CaseNote | Analyst-authored investigation note |
| CaseEvidence | File, link, JSON, screenshot, or note evidence |
| Report | Generated PDF, CSV, or JSON artifact |
| AuditLog | Redacted action record with actor, path, and timestamp |

## Constraints

- Account numbers are unique per organization.
- Transaction IDs are unique per organization.
- Risk score is one-to-one with a transaction.
- Behavior profile is one-to-one with a financial account.
- Case IDs are globally unique and generated as `FL-CASE-<org>-<random>`.
