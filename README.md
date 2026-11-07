# PayFlow — Payment Reconciliation Platform

An end-to-end payment reconciliation platform built to help payment operations teams reconcile payment instructions, processor events, settlement batches and bank statement records.

## Project Overview

PayFlow is a synthetic payment reconciliation system designed to demonstrate how financial transaction records can be processed, matched, investigated and audited.

The platform provides a centralized interface for monitoring payment transactions, identifying reconciliation discrepancies, managing exceptions and reviewing operational activity.

## Key Features

- **Payment Management:** View and monitor payment transactions and payment attempts.
- **Settlement Processing:** Manage settlement batches and settlement line items.
- **Automated Reconciliation:** Compare expected settlements against bank statement records.
- **Exception Management:** Identify, investigate and resolve reconciliation discrepancies.
- **Audit Trail:** Maintain traceability of analyst actions and exception state changes.
- **Reports & Analytics:** Visualize transaction, reconciliation and exception metrics.
- **Synthetic Data Generation:** Generate structured payment and settlement datasets.
- **Settings:** Manage application preferences and notification settings.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL 16 |
| Data Processing | Python, Pandas / CSV workflows |
| API Documentation | FastAPI / Swagger UI |
| Infrastructure | Docker, Docker Compose |

## System Architecture

The application follows a frontend–backend–database architecture.

1. The React frontend provides the operations dashboard and management interfaces.
2. FastAPI exposes REST endpoints for transactions, reconciliation, exceptions, audit history and reports.
3. PostgreSQL stores payment, processor, settlement, bank and reconciliation records.
4. Synthetic data generation scripts create structured datasets for testing reconciliation workflows.

## Business Workflow

1. Create merchant and payment order records.
2. Generate payment attempts and processor events.
3. Process captured and refunded transaction records.
4. Aggregate settlement records and calculate applicable fees.
5. Generate bank statement records.
6. Match settlement and bank records using reconciliation rules.
7. Identify unmatched or partially matched records.
8. Create exceptions for discrepancies.
9. Investigate and resolve exceptions.
10. Record relevant operational actions in the audit history.

## Core Data Entities

- Merchant
- PaymentOrder
- PaymentAttempt
- ProcessorEvent
- SettlementBatch
- SettlementLine
- BankStatementLine
- ReconciliationMatch
- Exception
- Resolution

Refer to [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for the available data dictionary.

## Project Structure

```text
payment-reconciliation/
├── app/
│   ├── generator.py
│   ├── bank_generator.py
│   ├── load_database.py
│   ├── reconciliation.py
│   ├── settlement.py
│   └── main.py
├── data/
│   └── generated/
├── db/
│   ├── schema.sql
│   └── database migrations
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── DATA_DICTIONARY.md
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11
- Node.js and npm
- Docker Desktop
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Babitha-Banothu/payflow-payment-reconciliation.git

cd payflow-payment-reconciliation
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

Configure the database connection using the environment variables required by the backend. Do not commit credentials or `.env` files.

### 3. Set up the Python backend

```bash
python3.11 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload --log-level debug
```

Backend URL:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

### 4. Set up the frontend

Open another terminal:

```bash
cd frontend

npm install

npm run dev
```

Open the local URL displayed by Vite, usually:

`http://localhost:5173`

## Synthetic Data

The project includes generated CSV and JSON datasets under `data/generated/`.

These datasets support payment, processor, settlement, bank statement and reconciliation workflows.

The project uses synthetic records rather than confidential customer or financial information.

See the generated manifest and data dictionary for additional information about the available data.

## API Modules

The backend provides endpoints for:

- Health checks
- Payment transactions
- Reconciliation records
- Exception management
- Exception investigation and resolution
- Audit history
- Reports and analytics

Explore the available endpoints through Swagger UI at `/docs`.

## Security and Data Handling

- Database credentials are kept outside the public repository.
- Environment files and Python virtual environments are excluded through `.gitignore`.
- Synthetic data is used for demonstration and development.

## Current Scope and Limitations

This is a development-stage demonstration built using synthetic data.

Dataset scale, anomaly coverage, automated validation and evaluation metrics should be interpreted according to the currently implemented generator, tests and generated records. The repository should not be treated as a production payment-processing system.

## Author

**Babitha Banothu**

GitHub: [Babitha-Banothu](https://github.com/Babitha-Banothu)

Project: [PayFlow Payment Reconciliation](https://github.com/Babitha-Banothu/payflow-payment-reconciliation)
