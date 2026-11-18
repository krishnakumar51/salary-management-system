# Design Decisions

The decisions that shape the system, each tied to code or evidence in this repository. A longer table (28 entries) is kept in [acme-salary-management/docs/decisions.md](../acme-salary-management/docs/decisions.md); this page explains the important ones and the alternatives not taken.

## 1. Technology choices

| Choice | Why it fits | Alternative / trade-off |
|---|---|---|
| **FastAPI + Pydantic v2** (required stack) | Typed request/response models give validation and an OpenAPI schema for free; the app runs unchanged as a Vercel Python Function (`app/main.py` exposes `app`) | A heavier framework adds nothing for a request/response API of 24 operations |
| **SQLAlchemy 2.0, synchronous**, psycopg 3 | Simple and correct for short-lived requests; the same models drive migrations and tests | Async would add complexity without a benefit here (no long-lived connections on serverless) |
| **Layered backend**: routes → services → repositories → models | Business rules (increments, transactions, conversion) are testable without HTTP; routes stay thin | More files than putting logic in route functions |
| **React + TypeScript + Vite, Tailwind v4, Radix-based shadcn-style components, TanStack Query, Recharts** (required stack) | Typed API contracts (`src/types/api.ts`); cached server state with loading/error handling; accessible dialog and menu primitives | A global state library was not needed because server state is in Query and filters are in the URL |
| **PostgreSQL on Neon**, **Vercel** (required) | Managed Postgres with a pooled endpoint suits short-lived serverless requests | Pooling by the driver in addition to Neon's pooler would double-pool, so production uses `NullPool` |

## 2. Database design

- **Two tables for pay.** `compensation` holds the *current* pay (one row per employee); `salary_history` holds every change. Reads of current pay (directory, analytics) are plain joins, and the ledger is append-only. *Alternative:* derive current pay from the latest history row; rejected because every directory and analytics query would need a "latest row per employee" subquery.
- **Constraints do the policing, not just the application.** `CHECK` constraints for non-negative amounts, currency ∈ {INR, USD, EUR}, frequency, status, employment type, `manager_id <> id`, `rate > 0`, base ≠ target currency; unique `employee_code`, `email` (stored lower-case), one compensation per employee, one rate per pair and date.
- **History immutability is enforced in the database** by a `BEFORE UPDATE OR DELETE` trigger on `salary_history` (created in the Alembic migration and in the model DDL). Tests confirm an `UPDATE` and a `DELETE` are rejected. *Trade-off:* the trigger is PostgreSQL-specific, which is why the tests run on real PostgreSQL.
- **One transaction per salary change**, with a row lock on the compensation row: compensation update, history row and audit row commit together or not at all. The lock prevents two simultaneous changes from losing an update; it is implemented but has **not** been tested under concurrent load.
- **Business rules that protect the ledger:** the effective date cannot be earlier than the current one; the result cannot be negative; terminated employees' pay is frozen. Employees are terminated, never deleted, so history is retained.
- **Indexes** match the directory: single-column indexes on department, country, status, designation, joining date and manager; a composite `(last_name, first_name)`; unique indexes on code and email; history indexed by `(employee_id, effective_date, id)`.
- **No PostgreSQL enums**: `String` columns with `CHECK` constraints, which keep migrations simple.

## 3. Money and multi-currency handling

- **No floats for money.** `NUMERIC(14,2)` columns, `Decimal` in Python, JSON money as strings, `decimal.js` for browser previews. Rounding is half-up to cents on both sides (a bug where the first conversion helper rounded half-even was caught by a unit test).
- **Original currency is the stored truth.** Reporting-currency views convert at read time; nothing is rewritten. The `exchange_rates` table keeps base, target, rate (`NUMERIC(18,8)`), effective date and a source note.
- **Rate resolution:** direct rate, then the inverse of the opposite pair, then triangulation through USD (so INR ↔ EUR works with only USD pairs). The latest rate on or before today is used, and its date is returned with every analytics response and shown in the UI.
- **Comparing different pay frequencies:** annualised as monthly × 12 and hourly × 2,080, in one reusable SQL expression so filters, sorting and analytics always agree.
- **Exact conversion arithmetic.** A rate is kept as a fraction (`numerator / denominator`) and SQL computes `amount × num ÷ den`. This was a fix: with a pre-rounded multiplier, EUR 46,000 (exactly USD 50,000 at 0.92) fell just below the boundary and was dropped from an inclusive "min 50,000" filter. A regression test covers it.
- **Rates are entered by HR (Settings page) or seeded**, because the brief rules out a paid FX API. *Trade-off:* rates can go stale, and analytics use the latest rate rather than each salary's historical rate.
- **Seed assumption:** only three currencies exist, so seeded UK payroll is EUR and Singapore/Canada are USD.

## 4. Search, filtering and pagination
- All of it runs in PostgreSQL; the browser never receives all 10,000 rows. Page size is capped at 100.
- Name/ID/email search is `ILIKE` over the full name, employee code and email, with `%`, `_` and `\` escaped, and every whitespace-separated term must match. *Alternative:* a `pg_trgm` index; not used (works without extensions, fast enough at this size). See [testing-and-performance.md](testing-and-performance.md).
- Offset pagination with a stable `id` tie-break (needed for page numbers and jump-to-page). *Alternative:* keyset pagination; not implemented.

## 5. Security and serverless
- **Auth:** bcrypt, JWT HS256, bearer header, no cookies, so no CSRF surface and no cookie-domain issue between two Vercel domains. *Trade-off:* the token lives in `localStorage` (readable by script if an XSS flaw existed) and there is no login rate limiting. An HttpOnly-cookie BFF would be the hardening step. There are no roles; one persona.
- **Secrets only from environment variables;** `JWT_SECRET` must be at least 16 characters; nothing has a default. `.env` files are git-ignored.
- **Two database URLs.** The API uses Neon's pooled URL (`DATABASE_URL`); migrations and the bulk seed use the direct URL (`DATABASE_URL_DIRECT`, optional). One engine factory (`app/db/engine.py`) applies the pooler-specific options.
- **`postgresql+pg8000://` fallback driver.** Added because psycopg's compiled module is blocked by Windows Application Control on the development machine. Production uses psycopg. Running the read paths through pg8000 exposed real defects (see [testing-and-performance.md](testing-and-performance.md)).
- **Frontend refuses to guess the API URL in production:** without `VITE_API_BASE_URL` a production build fails requests with a clear message instead of calling `localhost`.

## 6. Seed data
Deterministic (fixed seed, no clock dependence), idempotent (skips existing employee codes/emails), single transaction, run as a standalone script. Inserts use multi-row `INSERT ... VALUES` chunks of 500 rows so a remote database costs one round trip per chunk instead of one per row.

## 7. UX decisions that carry business meaning
- Salary changes go form → review → confirm; termination needs confirmation.
- The directory keeps filters, sort and page in the URL (shareable, back-button friendly); search and salary inputs are debounced.
- Every data view has loading, empty and error states; converted figures always show which rates and date were used.
