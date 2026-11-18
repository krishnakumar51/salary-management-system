# Architecture

## Overview
```
 Browser (React SPA, Vercel CDN)
        │  HTTPS + JWT (Authorization header)
        ▼
 FastAPI app  ── Vercel Python Function (stateless, one invocation per request)
        │  SQLAlchemy 2.0 (NullPool in production)
        ▼
 Neon PostgreSQL (pooled connection string)

 Out-of-band, never inside a request (use the DIRECT Neon URL, DATABASE_URL_DIRECT):
   python -m alembic upgrade head   → schema
   python -m seed.run               → 10,000-employee dataset
```

## Backend layers (`backend/app`)
| Layer | Responsibility |
|---|---|
| `api/routes` | HTTP only: parse/validate request (Pydantic), call a service, shape the response. No business rules. |
| `schemas` | Pydantic request/response models. Money is `Decimal` (serialised as strings). |
| `services` | Business rules and transactions: `compensation` (increments, history, atomicity), `employees`, `currency` (rate resolution/conversion), `analytics`, `auth`, `audit`. |
| `repositories` | Query construction: employee search/filter/sort/pagination, analytics aggregates, reusable SQL expressions (annualise + convert). |
| `models` | SQLAlchemy models, constraints, indexes, the immutability trigger DDL. |
| `core` | Settings (env), error envelope, JWT/bcrypt, constants. |
| `db` | `engine.py` is the single engine factory (app, Alembic, seed): disables prepared statements on Neon `-pooler` hosts, and supports a `postgresql+pg8000://` fallback driver with verifying TLS. `session.py` uses `NullPool` when `APP_ENV=production`. |

`app/main.py` exposes `app` (FastAPI) — the zero-config entrypoint Vercel detects. `/health` is liveness; `/health?deep=true` also checks the database.

## Frontend (`frontend/src`)
React + TypeScript + Vite, Tailwind v4, shadcn-style components (Radix primitives), TanStack Query for server state, Recharts for charts, `decimal.js` for client-side money previews.

| Folder | Role |
|---|---|
| `pages` | Route components (thin). |
| `features/{employees,compensation,dashboard,analytics}` | Feature UI + logic (directory, forms, increment dialog, charts). |
| `services` | `api.ts` fetch client (token, error envelope → `ApiError`), `endpoints.ts` typed calls. |
| `hooks` | Auth, reporting currency, debounce, lookups, page title/breadcrumbs. |
| `lib` | Formatting, validation, increment calculation. |
| `components` | Layout (sidebar + top bar), shared states, pagination, confirm dialog, UI primitives. |

Directory filters/sort/page live in the **URL query string** (shareable, back-button friendly). The reporting currency is a context persisted in `localStorage`.

## Data flow: applying a percentage increment
1. UI previews with `decimal.js` (identical ROUND_HALF_UP rule), user confirms.
2. `POST /api/v1/compensation/{id}/increment`.
3. Service opens a transaction, **locks** the compensation row (`SELECT … FOR UPDATE`), validates (not terminated, effective date ≥ current), computes the new amount with `Decimal`.
4. Updates `compensation`, inserts `salary_history` (previous/new amount, currency, frequency, %, amount, effective date, reason, user), inserts `audit_logs`; **one commit**. Any failure rolls back all three.
5. UI invalidates queries; profile, directory, dashboard refetch.

## Data flow: reporting-currency analytics
1. Request carries `currency=EUR` (selector in the top bar).
2. Service loads the latest rate per pair on/before today in **one query**, resolves each of INR/USD/EUR → EUR (direct, inverse, or via USD).
3. Repository builds a SQL expression `amount × annualisation-factor × rate` and runs `AVG`, `percentile_cont`, `MIN/MAX`, `SUM`, counts in PostgreSQL.
4. Response includes `rate_info` (rates used + the effective date); the UI prints it under every converted view. Stored salaries are never modified.

## Serverless considerations
No in-process state, sessions, background tasks or local files; JWT is stateless; all state is in Postgres. Connection management is delegated to Neon's pooler. Migrations/seed are CLI tools run from a developer machine/CI.
