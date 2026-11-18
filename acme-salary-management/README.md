# ACME Salary Management System

A centralised web application that replaces ACME's Excel-based salary tracking. An HR Manager can search ~10,000 employees, manage profiles, change compensation (fixed or percentage increments) with an immutable history, and analyse pay across countries and currencies (INR / USD / EUR) in a chosen reporting currency.

> Built for the Incubyte assessment. Design docs live in [`docs/`](docs): [requirements](docs/requirements.md) · [architecture](docs/architecture.md) · [database design](docs/database-design.md) · [decisions](docs/decisions.md) · [implementation plan & status](docs/implementation-plan.md).

## Technology
| Layer | Stack |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, psycopg 3, PyJWT, bcrypt, `Decimal` money |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4, shadcn-style components (Radix), Lucide, Recharts, TanStack Query |
| Database | PostgreSQL (Neon in production) |
| Tests | Pytest + HTTPX/TestClient (real PostgreSQL), Vitest + React Testing Library |
| Hosting | Vercel (frontend), Vercel Python Functions (FastAPI), Neon |

## Features
- **Dashboard**: headcount by country/department/status, totals per original currency, average/median/min/max, salary bands, recent changes. All values come from the database.
- **Directory**: server-side search (name, employee ID, email), filters (department, country, designation, status, salary range), sort (name, joining date, salary), pagination with page size, clear-all, loading/empty/error states. State lives in the URL.
- **Profile**: full details, manager, current pay, salary history; create / edit / terminate (confirmed).
- **Compensation**: add or update pay, change currency/frequency, fixed & percentage increments with live preview and a confirmation step. Example: INR 1,500,000 + 10% → INR 1,650,000 (increment INR 150,000), recorded in history in one transaction.
- **History**: append-only (database trigger), chronological, with who/when/why.
- **Analytics**: average and median by department, distribution by country/department, employees by salary band, trends, currency breakdown, all converted using stored exchange rates; the rate date is displayed.
- **Currency**: salaries keep their original currency; reporting currency selector (INR/USD/EUR); manual exchange rates (Settings).
- **Security**: bcrypt, JWT, protected APIs, CORS allow-list, validation on client and server, secrets only via environment variables.

## Repository layout
```
backend/   FastAPI app (app/), tests/, seed/, alembic/, Dockerfile, vercel.json
frontend/  React app (src/), vercel.json
docs/      requirements, architecture, database design, decisions, plan
docker-compose.yml
```

---

## Local setup (without Docker)

Prerequisites: Python 3.12+, Node 20+, a PostgreSQL 14+ database (or see "No Postgres?" below).

### 1. Backend
```bash
cd backend
python -m venv .venv
# macOS/Linux: source .venv/bin/activate      Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # or: pip install ".[server]" for runtime only
cp .env.example .env               # then edit .env (see "Environment configuration")
alembic upgrade head               # create the schema
python -m seed.run                 # load 10,000 employees (≈25 s locally)
uvicorn app.main:app --reload --port 8000
```
API docs: <http://localhost:8000/docs> (disabled when `APP_ENV=production`).

**No Postgres installed?** `python scripts/dev_postgres.py` starts an embedded PostgreSQL (via the `pgserver` dev dependency) and prints a `DATABASE_URL` to put in `.env`. Stop it with `python scripts/dev_postgres.py --stop`.

### 2. Frontend
```bash
cd frontend
npm install
cp .env.example .env               # VITE_API_BASE_URL=http://localhost:8000
npm run dev                        # http://localhost:5173
```
Sign in with `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` from your backend `.env`.

## Environment configuration
**Backend (`backend/.env`)**
| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Used by the running API. `postgresql://user:pass@host/db?sslmode=require`. With Neon use the **pooled** string (host contains `-pooler`). `postgres://` / `postgresql://` are normalised to the psycopg 3 driver; `-pooler` hosts automatically disable prepared statements. |
| `DATABASE_URL_DIRECT` | no | Used by **Alembic and the seed script**. With Neon use the **direct** string (same host without `-pooler`). Falls back to `DATABASE_URL` when unset. Not needed on Vercel. |
| `JWT_SECRET` | yes | ≥ 16 chars. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | yes | Comma-separated allowed frontend origins, e.g. `http://localhost:5173`. |
| `APP_ENV` | no | `development` (default) or `production` (serverless pooling, API docs off). |
| `JWT_EXPIRE_MINUTES` | no | default 480. |
| `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, `SEED_ADMIN_NAME` | seed only | HR account the seed script creates. Never read by the web app. |

**Frontend (`frontend/.env`)**: `VITE_API_BASE_URL` — backend base URL, no trailing slash, no `/api/v1`.

No secret has a default; nothing is hard-coded.

## Database migrations
```bash
cd backend
alembic upgrade head      # apply
alembic downgrade base    # revert everything
alembic check             # verify models and migrations agree
```
Migrations are run by you (or CI), **never inside a serverless request**. Alembic reads `DATABASE_URL_DIRECT` (Neon's **direct, non-pooled** string) and falls back to `DATABASE_URL`.

## Seeding
The seed is a standalone, deterministic (`seed=20260101`), re-runnable script. It creates countries, departments, exchange rates, the HR user, 10,000 employees with compensation, managers, and ~23,000 salary-history rows (single transaction). Re-running skips employees that already exist (matched by employee code or email), so nothing is duplicated.
```bash
python -m seed.run                       # 10,000 employees into $DATABASE_URL
python -m seed.run --count 500           # smaller set
```
**Against Neon**: put both Neon strings in `backend/.env` (`DATABASE_URL` = pooled, `DATABASE_URL_DIRECT` = direct; never commit `.env`), then:
```bash
cd backend
alembic upgrade head          # reads DATABASE_URL_DIRECT
python -m seed.run            # reads DATABASE_URL_DIRECT (about 1-2 minutes over the internet)
```
Verify the employee count by running `select count(*) from employees;` in the Neon SQL Editor (expect 10000), or:
```bash
python -c "from sqlalchemy import text; from app.core.config import get_settings as g; from app.db.engine import build_engine as b; print(b(g().migration_database_url).connect().execute(text('select count(*) from employees')).scalar())"
```
A one-off URL also works: `python -m seed.run --database-url "<direct url>"`.

> **Windows Application Control / blocked psycopg:** use the pure-Python fallback. `pip install pg8000` (or `pip install -e ".[pg8000]"`) and write the scheme as `postgresql+pg8000://...` in `.env`. The app, Alembic and the seed all go through `app/db/engine.py`, which turns `sslmode=require` into a verifying TLS context for pg8000.
Seeded exchange rates are *indicative* (1 USD = 83.25 INR = 0.92 EUR, effective 2026-01-01). Update them under **Settings → Exchange rates**.

> Data assumption: only INR/USD/EUR are supported, so United Kingdom payroll is in EUR and Singapore/Canada in USD (documented in [decisions](docs/decisions.md)).

## Running tests
```bash
# Backend (starts an embedded PostgreSQL automatically; or set TEST_DATABASE_URL)
cd backend && pytest
# Frontend
cd frontend && npm test            # npm run typecheck for tsc
```
Backend tests deliberately run on **real PostgreSQL** (triggers, `percentile_cont`, row locks, NUMERIC). They cover employee CRUD, search/filter/sort/pagination (+ an N+1 guard), increments (fixed/percentage/rounding), history creation, currency validation and conversion, invalid input, transaction rollback, history immutability, auth, analytics and the seed. Frontend tests cover directory rendering, search, filters, pagination, sorting, increment calculation/preview/confirmation, form validation, and loading/error/empty states.

## Docker
```bash
cp .env.example .env           # set POSTGRES_PASSWORD, JWT_SECRET, SEED_ADMIN_*
docker compose up --build      # db + API (runs migrations) + Vite dev server
docker compose run --rm backend python -m seed.run
```
App <http://localhost:5173> · API <http://localhost:8000/docs>. *(Compose files were written but could not be executed on the machine this was built on — Docker was not installed — so treat them as unverified.)*

## Deployment: Vercel + Neon
Two separate Vercel projects from the same GitHub repo. No Railway/Render, nothing deploys automatically.

### 1. Neon (database)
1. Create a Neon project and database.
2. Copy **two** connection strings from the dashboard: **Direct** (for migrations/seed) and **Pooled** (host contains `-pooler`, for the API).
3. Put them in `backend/.env` as `DATABASE_URL_DIRECT` / `DATABASE_URL`, then run migrations and the seed from your machine (see *Seeding*). On Vercel set only `DATABASE_URL` (pooled).

### 2. Backend project (FastAPI on Vercel Python Functions)
1. Push the repo to GitHub. In Vercel: **Add New → Project**, import the repo.
2. **Root Directory:** `backend` (if this folder is nested in a larger repo, e.g. `acme-salary-management/backend`).
3. Framework preset: *Other* / auto-detected (Vercel detects `app/main.py` exposing `app`; dependencies come from `pyproject.toml`; Python 3.12 via `.python-version`). No build command needed.
4. **Environment variables:**
   | Name | Value |
   |---|---|
   | `DATABASE_URL` | Neon **pooled** connection string |
   | `JWT_SECRET` | long random string |
   | `CORS_ORIGINS` | your frontend URL, e.g. `https://acme-salary.vercel.app` (comma-separate several) |
   | `APP_ENV` | `production` |
5. Deploy and check `https://<backend>.vercel.app/health` → `{"status":"ok"}`; `…/health?deep=true` also checks the database.

`APP_ENV=production` switches SQLAlchemy to `NullPool` with prepared statements off (required for PgBouncer transaction pooling) and disables `/docs`.

### 3. Frontend project (Vite SPA)
1. **Add New → Project**, import the same repo again.
2. **Root Directory:** `frontend`. Framework preset: *Vite* (build `npm run build`, output `dist`; `vercel.json` adds the SPA rewrite).
3. **Environment variable:** `VITE_API_BASE_URL` = the backend URL (e.g. `https://acme-salary-api.vercel.app`).
4. Deploy, then put the frontend's URL into the backend's `CORS_ORIGINS` and redeploy the backend.

### Notes
- Everything in production is stateless: JWT auth, no sessions, no background jobs, no local files.
- Cold starts of the function and of a suspended Neon compute can add a second or two to the first request.
- Never put the direct/pooled URL, `JWT_SECRET`, or seed credentials in the repo; set them in Vercel/your shell.

## API summary (`/api/v1`)
`POST /auth/login` · `GET /auth/me` · `GET/POST /employees` · `GET/PATCH /employees/{id}` · `GET /employees/{id}/salary-history` · `GET/POST /compensation` · `GET/PATCH /compensation/{id}` · `POST /compensation/{id}/increment[/preview]` · `GET /analytics/{dashboard,departments,countries,distribution,trends,currencies}?currency=` · `GET/POST /exchange-rates` · `GET /exchange-rates/convert` · `GET /lookups` · `GET /health`.
Errors: `{"error": {"code", "message", "details": [{"field","message"}]}}`.

## Measured on the seeded dataset (10,000 employees, local PostgreSQL)
Directory list ≈ 56 ms · text search ≈ 80 ms · filtered + salary-sorted ≈ 36 ms · dashboard ≈ 200 ms · analytics endpoints ≈ 25–70 ms.

## Known limitations
- Single HR role; users are created by the seed script (no user-management UI, no password reset).
- JWT is kept in `localStorage` (XSS trade-off) and there is no login rate-limiting (see [decisions](docs/decisions.md) #17/#18).
- Exchange rates are manual and analytics use the latest rate, not each salary's historical rate.
- Search uses `ILIKE`; at hundreds of thousands of rows add a `pg_trgm` index. Offset pagination slows on very deep pages.
- Employees are terminated, never deleted; compensation of terminated employees is frozen; effective dates cannot go backwards.
- Hourly pay is annualised at 2,080 hours; UK/Singapore/Canada payrolls use EUR/USD because only INR/USD/EUR are supported.
- Docker Compose and the Vercel/Neon deployment were configured but **not executed** by the author; the UI has had only a light manual check (one dashboard render) — please do a full walkthrough.
- On machines with Windows Application Control, the compiled `psycopg[binary]` module may be blocked. The test-suite falls back to psycopg's pure-Python mode automatically; for the app set `PSYCOPG_IMPL=python` and make `libpq` available on `PATH`.

## License
MIT
