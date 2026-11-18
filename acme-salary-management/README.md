# ACME Salary Management System

**A full-stack HR compensation management platform for organizations managing approximately 10,000 employees across multiple countries.** It replaces Excel-based salary tracking with a searchable employee directory, compensation management with a permanent salary history, multi-currency reporting (INR / USD / EUR) and compensation analytics.

*Built for the Incubyte Software Craftsperson assessment.*

**Built with:** React · TypeScript · Vite · Tailwind CSS · Python · FastAPI · SQLAlchemy · PostgreSQL · Neon · Vercel

---

## LIVE DEMO AND ASSESSMENT ACCESS

| Resource | Link |
|---|---|
| **Live application (frontend)** | <https://salary-management-system-theta.vercel.app/> |
| **Backend API** | <https://acme-salary-api.vercel.app> |
| **Backend health check** | <https://acme-salary-api.vercel.app/health> |
| **Backend deep health check** (also queries the database) | <https://acme-salary-api.vercel.app/health?deep=true> |
| **Loom demonstration** | <https://www.loom.com/share/d930b4ad9db94a119bf53edf16761781> |
| **Source code** | <https://github.com/krishnakumar51/salary-management-system> |

### Demo HR login (assessment demonstration credentials)

| | |
|---|---|
| **Email** | `hr.manager@acme-demo.com` |
| **Password** | `E585XxXpInjTX4WA` |

> **These are assessment demonstration credentials, not real employee or production credentials.** The account exists only so reviewers can try the application. All 10,000 employees, salaries and exchange rates in the demo database are **fictional, generated seed data**. Do not reuse this password for any personal or production account. Because the demo is shared, other visitors may have changed some records.

### How it is deployed

One GitHub monorepo, deployed as two separate Vercel projects plus a managed database:

| Part | Hosted on | Vercel project root directory | Notes |
|---|---|---|---|
| **Frontend** (React SPA) | **Vercel** | `acme-salary-management/frontend` | Vite build to `dist/`, single-page-app rewrite |
| **Backend** (FastAPI) | **Vercel Python Functions** | `acme-salary-management/backend` | Entrypoint `app/main.py`, Python 3.12, stateless requests |
| **Database** (PostgreSQL) | **Neon** | n/a | The API uses Neon's *pooled* connection; migrations and seeding run separately |

The database connection string, JWT secret and every other secret live only in the Vercel project settings (and in git-ignored local `.env` files). **None are stored in this repository.** Exact settings: [section 18](#18-production-deployment-vercel--neon) and the [deployment checklist](docs/deployment-checklist.md).

---

## Highlights

- Employee directory with **10,000 seeded records**.
- **Search, sorting, filtering and pagination**, all executed in PostgreSQL.
- Employee profiles and compensation management.
- **Percentage-based and fixed salary increments.**
- **Complete salary change history** (append-only; recorded in the same transaction as the change).
- **INR, USD and EUR** support, with every salary kept in its original currency.
- **Reporting-currency conversion** using stored exchange rates (the rate date is shown).
- **Department-wise and country-wise analytics.**
- **HR Manager authentication** (bcrypt + JWT).

## Verified quality

Results from the final verification run on 18 Nov 2026:

| Check | Result |
|---|---|
| Backend tests (pytest, real PostgreSQL) | **138 passing** |
| Frontend tests (Vitest + React Testing Library) | **50 passing** |
| TypeScript compilation (`tsc --noEmit`) | **Successful** |
| Production frontend build (`npm run build`) | **Successful** (also verified from a clean Git checkout) |
| Live backend `/health` and `/health?deep=true` | **Returned `{"status":"ok"}`** when checked |

Docker Compose was written but **not run** (Docker was unavailable); see [Known limitations](#20-known-limitations-and-deliberate-exclusions). Commands to re-run everything: [section 15](#15-running-tests).

## Documentation

[Requirements](docs/requirements.md) · [Architecture](docs/architecture.md) · [Database design](docs/database-design.md) · [Decisions & trade-offs](docs/decisions.md) · [Implementation status](docs/implementation-plan.md) · [Deployment checklist](docs/deployment-checklist.md)

## Engineering Documentation

The assessment's engineering artifacts live in [`docs/`](../docs/) at the repository root:

| Document | What it covers |
|---|---|
| [Requirements and scope](../docs/requirements-and-scope.md) | Problem understanding, functional and non-functional requirements traced to code and tests, deliberate exclusions and assumptions |
| [Architecture](../docs/architecture.md) | System overview with a diagram, responsibilities of frontend / backend / database / deployment, main data flows, the authentication flow, the 24-operation API surface |
| [Architecture diagram source](../docs/architecture.mmd) | The Mermaid source of that diagram |
| [Design decisions](../docs/design-decisions.md) | Technology choices, database design, multi-currency handling, search and pagination, security and serverless trade-offs, with alternatives not taken |
| [Testing and performance](../docs/testing-and-performance.md) | Test approach, counts per file, verification results, defects the verification found, seed-data scale, observed timings, limitations |
| [AI usage](../docs/ai-usage.md) | What the AI assistant did, what the human owner did, and how the output was checked |

**Architecture in brief:** a React + TypeScript single-page app (Vercel) calls a stateless FastAPI backend (Vercel Python Functions) with a JWT; the backend is layered (routes → services → repositories → models) and talks to Neon PostgreSQL through its pooled connection. Search, filtering, sorting, pagination and all analytics run in PostgreSQL; money is `NUMERIC`/`Decimal`; every salary change is one transaction that also writes an append-only history row.

**Two documentation sets:** `docs/` (above) holds the assessment artifacts; [`acme-salary-management/docs/`](docs/) holds implementation-level notes: [database design](docs/database-design.md), the full [decisions table](docs/decisions.md), the [implementation status](docs/implementation-plan.md) and the [deployment checklist](docs/deployment-checklist.md).

---

## 1. Problem statement
ACME has ~10,000 employees in several countries. HR tracks salaries in spreadsheets, which makes it slow to find a person, impossible to trust the history of a salary, and hard to see how pay is distributed, especially when salaries are in different currencies.

## 2. User persona
**HR Manager**: manages employee records and compensation, needs to answer "what do we pay engineers in Germany vs India?", and must be able to prove who changed a salary, when and why.

## 3. Features
| Area | What it does |
|---|---|
| **Dashboard** | Headcount (total, active, by country / department / status), pay totals per *original* currency, average / median / min / max, salary bands, recent salary changes. Reporting-currency selector in the top bar. |
| **Directory** | Server-side search (name, employee ID, email); filters (department, country, designation, status, salary range); sort (name, joining date, salary); pagination with page size; clear-all; loading / empty / error states. State is kept in the URL. |
| **Profile** | All profile fields, manager, current pay, salary history. Create, edit, terminate (confirmed). |
| **Compensation** | Add or update pay, change currency / frequency, fixed and percentage increments with live preview and a confirmation step, effective date and reason. |
| **Salary history** | Append-only ledger of every change (previous / new amount and currency, %, effective date, reason, HR user, timestamp). |
| **Analytics** | Average and median by department, distribution by country and department, headcount by salary band, change trends, breakdown by currency, all converted with stored exchange rates (rate date shown). |
| **Settings** | Account details; manage exchange rates. |
| **Auth** | HR login (JWT); every API except login and health is protected. |

## 4. Technology
| Layer | Stack |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, psycopg 3, PyJWT, bcrypt, `Decimal` money |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4, shadcn-style components (Radix), Lucide, Recharts, TanStack Query, decimal.js |
| Database | PostgreSQL (Neon in production) |
| Tests | Pytest on a real PostgreSQL; Vitest + React Testing Library |
| Hosting | Vercel (frontend), Vercel Python Functions (FastAPI), Neon |

## 5. Architecture overview
```
Browser (React SPA on Vercel) ──HTTPS + JWT──▶ FastAPI (Vercel Python Function) ──SQLAlchemy──▶ Neon PostgreSQL (pooled)
                                         migrations + seed run separately from your machine (direct connection)
```
Backend layers: `api/routes` (HTTP only) → `services` (business rules, transactions) → `repositories` (queries) → `models` (schema). Stateless by design: JWT auth, no sessions, background jobs or local files, so it suits short-lived serverless requests. See [architecture](docs/architecture.md).

## 6. Directory structure
```
acme-salary-management/
├── backend/
│   ├── app/            api/routes, core, db, models, repositories, schemas, services, main.py
│   ├── alembic/        migrations (0001_initial_schema)
│   ├── seed/           deterministic 10,000-employee generator + runner
│   ├── scripts/        dev_postgres.py (embedded Postgres when Docker/Postgres is unavailable)
│   ├── tests/          pytest suite
│   ├── Dockerfile  vercel.json  .python-version  pyproject.toml  .env.example
├── frontend/
│   ├── src/            pages, features/{dashboard,employees,compensation,analytics}, components, hooks, services, lib, types, test
│   └── vercel.json  package.json  .env.example
├── docs/               requirements, architecture, database design, decisions, plan, deployment checklist
├── docker-compose.yml  .env.example  LICENSE
```

## 7. Database design (summary)
`countries`, `departments`, `employees` (self-referencing `manager_id`), `compensation` (**current** pay, one row per employee), `salary_history` (**append-only** ledger), `exchange_rates`, `users`, `audit_logs`.
- Unique employee code and email (email stored lower-case); `CHECK` constraints for non-negative amounts, currency ∈ {INR, USD, EUR}, frequency, status, employment type.
- `NUMERIC(14,2)` money, `NUMERIC(18,8)` rates. No floats.
- A database trigger rejects `UPDATE` / `DELETE` on `salary_history`.
- B-tree indexes on the directory filter/sort columns; unique indexes on code and email.
Details: [database design](docs/database-design.md).

## 8. Currency handling
- Every salary keeps its **original currency**; converting for reporting never modifies stored data.
- `exchange_rates` stores `base → target`, rate, effective date and a source note. Rates are entered by HR in *Settings* (or seeded); no paid FX API is used.
- Resolution: direct rate → inverse → triangulation through USD (so INR ↔ EUR works with only USD pairs). The latest rate on or before today is used and its **date is displayed** with every converted view.
- Pay of different frequencies is compared as annual-equivalent (monthly × 12, hourly × 2,080). Conversion runs in SQL with exact fractions (`amount × num ÷ den`), so values on a boundary (EUR 46,000 = USD 50,000) are included in inclusive filters.
- Analytics cover employees with pay who are not terminated; headcounts include everyone.
- Seed-data assumption: only INR/USD/EUR exist, so UK payroll is in EUR, Singapore and Canada in USD.

## 9. Salary increments and history
- **Percentage:** `new = current + round_half_up(current × p / 100, 2)`. Example: INR 1,500,000 + 10% → INR 1,650,000 (increment INR 150,000).
- **Fixed:** `new = current + amount`; the equivalent percentage is stored too.
- **Update** sets a new amount and optionally a new currency and/or frequency (the UI can propose the current amount converted at the latest rate).
- Each change runs in **one transaction**: lock the compensation row → validate → update `compensation` → insert `salary_history` → insert `audit_logs` → commit. Any failure rolls all three back.
- Rules: effective date cannot be earlier than the current one; the result cannot be negative; terminated employees' pay is frozen. The UI previews with `decimal.js` using the same rounding, then asks for confirmation.

## 10. Authentication and security
- Passwords are stored as **bcrypt** hashes; login returns a signed **JWT** (HS256, default 8 h) sent as `Authorization: Bearer`. Unknown email and wrong password give the same response.
- No secret has a default: `JWT_SECRET` (≥ 16 chars), database URLs and seed credentials come from environment variables. `.env` files are git-ignored.
- CORS is an explicit allow-list (`CORS_ORIGINS`); inputs are validated on client and server; API docs are disabled when `APP_ENV=production`.
- Trade-offs (JWT in `localStorage`, no login rate-limit) are in [decisions](docs/decisions.md).

## 11. Local development setup
Prerequisites: Python 3.12+, Node 20+, PostgreSQL 14+ (or the embedded option below).
```bash
# Backend
cd backend
python -m venv .venv                       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                       # edit it (section 12)
python -m alembic upgrade head
python -m seed.run                         # 10,000 employees
python -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env                       # VITE_API_BASE_URL=http://localhost:8000
npm run dev                                # http://localhost:5173
```
Sign in with `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` from your backend `.env`. API docs: `http://localhost:8000/docs`.
**No Postgres?** `python scripts/dev_postgres.py` starts an embedded one and prints a `DATABASE_URL`.
*Tip: `python -m <tool>` avoids blocked `.exe` launchers on locked-down Windows machines.*

## 12. Environment variables
**Backend: `backend/.env` locally, Vercel project settings in production** (code: `app/core/config.py`, `seed/run.py`, `alembic/env.py`)
| Variable | Used by | Required | Example / notes |
|---|---|---|---|
| `DATABASE_URL` | API | **Yes** | **Pooled** Neon URL: `postgresql://USER:PASSWORD@ep-xxxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require` |
| `DATABASE_URL_DIRECT` | Alembic, seed | Optional (falls back to `DATABASE_URL`) | **Direct** Neon URL (same host without `-pooler`). Not needed on Vercel |
| `JWT_SECRET` | API | **Yes** | ≥ 16 chars; `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | API | **Yes** (defaults to `http://localhost:5173`) | Comma-separated exact origins, e.g. `https://acme-salary.vercel.app` |
| `APP_ENV` | API | Recommended | `development` (default) or `production` (serverless pooling, `/docs` off) |
| `JWT_EXPIRE_MINUTES` | API | No | default `480` |
| `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` (≥ 8), `SEED_ADMIN_NAME` | Seed only | For seeding | HR account to create. Never read by the web app |
| `TEST_DATABASE_URL` | pytest | No | Use an existing Postgres for tests; refused if it is a `.neon.tech` host |

**Frontend: `frontend/.env` locally, Vercel project settings in production**
| Variable | Required | Example |
|---|---|---|
| `VITE_API_BASE_URL` | **Yes** (build-time) | `https://acme-salary-api.vercel.app` (no trailing slash, no `/api/v1`). A production build without it refuses to call any API |

**Docker Compose** (root `.env`): `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET`, `SEED_ADMIN_*`.

> Pooled vs direct: Neon's pooler (PgBouncer) suits short-lived requests, so the **API uses the pooled URL**. Migrations and the bulk seed use the **direct URL**. Pooled hosts automatically disable prepared statements. If psycopg cannot load on your machine, install `pg8000` and write the scheme as `postgresql+pg8000://` (see section 15).

## 13. Database migrations
```bash
cd backend
python -m alembic upgrade head      # apply (uses DATABASE_URL_DIRECT, else DATABASE_URL)
python -m alembic current           # expect: 0001 (head)
python -m alembic check             # models and migrations agree
python -m alembic downgrade base    # revert everything (local use only)
```
Migrations run from your machine or CI, never inside a serverless request.

## 14. Seeding 10,000 employees
```bash
python -m seed.run                  # 10,000 employees; or --count 500
```
Deterministic (`seed=20260101`), idempotent (existing employees are skipped by code or email) and a single transaction. It creates countries, departments, exchange rates (indicative: 1 USD = 83.25 INR = 0.92 EUR, effective 2026-01-01; update them in Settings), the HR user, 10,000 employees with compensation and managers, and ~23,000 history rows. About 25 s locally and ~75 s to Neon.
Verify the count: `select count(*) from employees;` should return `10000` (Neon SQL Editor, or `psql`).

## 15. Running tests
```bash
cd backend && python -m pytest        # 138 tests; starts an embedded PostgreSQL (pgserver) or uses TEST_DATABASE_URL
cd frontend && npm test               # 50 tests (Vitest + React Testing Library)
cd frontend && npm run typecheck      # tsc --noEmit
```
Backend tests run on real PostgreSQL (triggers, `percentile_cont`, row locks, NUMERIC). They cover employee CRUD, search / filter / sort / pagination (with an N+1 guard), increments and rounding, history, currency validation and conversion, invalid input, transaction rollback, history immutability, auth, analytics, the seed, and the read paths through the pure-Python `pg8000` driver. Frontend tests cover directory rendering, search, filters, sorting, pagination, increment preview / confirmation, form validation, password toggle, and loading / error / empty states.
*Locked-down Windows machines may block psycopg's compiled module. The test suite falls back automatically; for the app use `pip install pg8000` and a `postgresql+pg8000://` URL.*

## 16. Building the frontend
```bash
cd frontend && npm run build          # tsc -b && vite build  -> dist/
npm run preview                       # serve the production build locally
```

## 17. Docker
```bash
cp .env.example .env                  # set POSTGRES_PASSWORD, JWT_SECRET, SEED_ADMIN_*
docker compose up --build             # PostgreSQL + API (runs migrations) + Vite dev server
docker compose run --rm backend python -m seed.run
```
App `http://localhost:5173`, API `http://localhost:8000/docs`. **The Compose files were written but never executed**: Docker is not installed on the machine this was built on. Treat them as unverified.

## 18. Production deployment (Vercel + Neon)
Two Vercel projects from one GitHub repo (live URLs at the top of this README). Nothing deploys automatically; the steps below are manual. Use the [deployment checklist](docs/deployment-checklist.md) to track them.

### 18.1 Neon
1. Create a Neon project/database. From **Connect**, copy both strings: **Pooled** (host contains `-pooler`) and **Direct**.
2. Put them in `backend/.env` as `DATABASE_URL` (pooled) and `DATABASE_URL_DIRECT` (direct), plus `JWT_SECRET` and `SEED_ADMIN_*`.
3. `python -m alembic upgrade head`, then `python -m seed.run`, then verify `select count(*) from employees;` = 10000.

### 18.2 Backend project (FastAPI on Vercel Python Functions)
| Setting | Value |
|---|---|
| Root Directory | `acme-salary-management/backend` |
| Framework Preset | Other (Vercel auto-detects the FastAPI app: `app/main.py` exposes `app`) |
| Build / Output / Install | defaults (no build command, no output directory) |
| Python | 3.12 (`backend/.python-version`; `requires-python = ">=3.12"`) |
| Dependencies | `backend/pyproject.toml` `[project].dependencies` (optional extras are not installed) |
| Function config | `backend/vercel.json`: `functions."app/main.py".maxDuration = 30` |
| Excluded from upload | `backend/.vercelignore` (tests, seed, alembic, scripts, Docker files, `.env`) |

Environment variables (Production, and Preview if you use it):
| Name | Value |
|---|---|
| `DATABASE_URL` | Neon **pooled** URL |
| `JWT_SECRET` | long random string |
| `CORS_ORIGINS` | the frontend's exact origin, e.g. `https://acme-salary.vercel.app` (comma-separate several; no trailing slash) |
| `APP_ENV` | `production` |

`APP_ENV=production` makes SQLAlchemy use `NullPool` (Neon's pooler does the pooling) and disables `/docs`. `DATABASE_URL_DIRECT` and `SEED_ADMIN_*` are **not** needed on Vercel.
Health: `GET https://<backend>/health` → `{"status":"ok"}`; `GET https://<backend>/health?deep=true` also queries the database.

### 18.3 Frontend project (Vite SPA)
| Setting | Value |
|---|---|
| Root Directory | `acme-salary-management/frontend` |
| Framework Preset | Vite |
| Build Command | `npm run build` (`frontend/vercel.json`) |
| Output Directory | `dist` (`frontend/vercel.json`) |
| Rewrites | all paths → `/index.html` (SPA routing, `frontend/vercel.json`) |
| Env var | `VITE_API_BASE_URL` = the backend's URL (build-time: **redeploy** after changing it) |

### 18.4 Order and verification
1. Deploy the backend → check `/health` and `/health?deep=true`.
2. Deploy the frontend with `VITE_API_BASE_URL` set.
3. Add the frontend's origin to the backend `CORS_ORIGINS` and **redeploy the backend**.
4. Verify in the browser: sign in; search and filter the directory; open a profile; add a test employee and apply an increment; check its history; switch the reporting currency; open Overview and Analytics.
```bash
curl https://<backend>/health
curl "https://<backend>/health?deep=true"
curl -i -X OPTIONS https://<backend>/api/v1/auth/login -H "Origin: https://<frontend>" -H "Access-Control-Request-Method: POST"   # expect access-control-allow-origin
```
Cold starts of the function and of a suspended Neon compute can add a second or two to the first request. Vercel preview deployments have different origins; add them to `CORS_ORIGINS` if you use them.

## 19. API summary (`/api/v1`)
`POST /auth/login` · `GET /auth/me` · `GET|POST /employees` · `GET|PATCH /employees/{id}` · `GET /employees/{id}/salary-history` · `GET|POST /compensation` · `GET|PATCH /compensation/{id}` · `POST /compensation/{id}/increment[/preview]` · `GET /analytics/{dashboard,departments,countries,distribution,trends,currencies}?currency=` · `GET|POST /exchange-rates` · `GET /exchange-rates/convert` · `GET /lookups` · `GET /health`. Errors use `{"error": {"code", "message", "details": [{"field","message"}]}}`.

## 20. Known limitations and deliberate exclusions
**Limitations**
- Single HR role; users come from the seed script (no user-management UI or password reset).
- JWT is stored in `localStorage` (XSS trade-off) and login has no rate limiting; put Vercel's firewall in front for real use.
- Exchange rates are manual; analytics use the latest rate, not each salary's historical rate.
- Search uses `ILIKE` (fine at 10k rows; add `pg_trgm` at much larger scale). Offset pagination slows on very deep pages.
- Employees are terminated, never deleted; pay of terminated employees is frozen; effective dates cannot go backwards.
- Hourly pay is annualised at 2,080 h; UK / Singapore / Canada payrolls use EUR / USD because only INR / USD / EUR are supported.
- Over the internet, a request to Neon (Singapore region) takes roughly 2-4 s end to end from some locations; against a local database the same calls take 25-200 ms.

**Not verified by the author:** Docker Compose (Docker was unavailable). The deployed app's `/health` and `/health?deep=true` were checked and the Neon database was migrated, seeded and queried through the API; the UI has no automated browser test and relies on component tests plus manual checking.

**Deliberately excluded** (see [requirements](docs/requirements.md)): LLM/AI features, Redis/Celery/background workers, microservices, a live FX API, multi-role RBAC/SSO, payroll/tax/benefits, hard-deleting employees, bulk import through the UI.

## License
MIT
