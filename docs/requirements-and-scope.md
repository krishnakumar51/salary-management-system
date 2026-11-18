# Requirements and Scope

## 1. Problem understanding
ACME is an organisation of roughly 10,000 employees in several countries. Its HR team keeps employee and salary data in Excel spreadsheets, which makes it slow to find a person, hard to trust the history of a salary, and difficult to see how pay is distributed, especially when pay is in different currencies.

**Primary user:** one persona, the **HR Manager**, who manages employees and compensation and needs to explain every salary change (who, when, why) and compare pay across departments and countries.

**Goal:** replace the spreadsheets with one web application: a searchable employee directory, compensation management with a permanent salary history, multi-currency reporting and compensation analytics.

The requirements below come from the assessment brief; the "Where implemented" and "Evidence" columns point at the code and tests that exist in this repository.

## 2. Functional requirements

| # | Requirement | Where implemented | Evidence |
|---|---|---|---|
| F1 | HR Manager sign-in; every API except login and health requires it | `backend/app/api/routes/auth.py`, `app/api/deps.py`; login page + route guard in the frontend | `tests/test_auth.py` (15) |
| F2 | Directory of 10,000 employees with search (name, employee ID, email), filters (department, country, designation, status, salary range), sort (name, joining date, salary), pagination and page size, all done server-side | `GET /api/v1/employees`; `features/employees/EmployeeDirectory.tsx` | `tests/test_search.py` (22), `EmployeeDirectory.test.tsx` (11); cross-checked against independent SQL on the Neon data |
| F3 | Employee profile with all required fields; create, edit and view | `POST/GET/PATCH /employees`; profile and form pages | `tests/test_employees.py` (24), `EmployeeForm.test.tsx` (5) |
| F4 | Compensation: add, update, fixed and percentage increments, change currency and frequency, effective date, reason | `/api/v1/compensation` (`POST`, `PATCH`, `/{id}/increment`, `/{id}/increment/preview`); increment and update dialogs | `tests/test_compensation.py` (29), `IncrementDialog.test.tsx` (5), `compensation.test.ts` (5) |
| F5 | Every change creates an immutable history record, written in the same transaction as the change, shown chronologically on the profile | `app/services/compensation.py`, `GET /employees/{id}/salary-history`, DB trigger on `salary_history` | `tests/test_compensation.py` (rollback, immutability, ordering) |
| F6 | INR, USD, EUR; original currency preserved; `exchange_rates` table; reporting-currency selector; rate date shown | `app/services/currency.py`, `/exchange-rates`, top-bar selector, Settings page | `tests/test_currency.py` (18), `tests/test_analytics.py` (11) |
| F7 | Dashboard: totals, active, by country / department / status, totals per currency, average, median, min / max by department, recent changes, distribution | `GET /analytics/dashboard`; `features/dashboard/Dashboard.tsx` | `tests/test_analytics.py` |
| F8 | Analytics page: average and median by department, distribution by country and department, employees per salary band, trends, currency breakdown | `/analytics/{departments,countries,distribution,trends,currencies}`; `features/analytics/` | `tests/test_analytics.py`, `tests/test_pg8000_driver.py` |
| F9 | Deterministic, re-runnable seed script for 10,000 employees, run outside HTTP | `backend/seed/` | `tests/test_seed.py` (6); run against Neon |
| F10 | Deployable on Vercel (frontend, FastAPI backend) with Neon | `frontend/vercel.json`, `backend/vercel.json`, `backend/app/main.py` | Live `/health` and `/health?deep=true` returned `{"status":"ok"}` on 18 Nov 2026 |

The API surface is 24 operations (listed in [architecture.md](architecture.md)).

## 3. Non-functional requirements

| Requirement | How it is met | Evidence |
|---|---|---|
| **Money correctness**: no floating point for money | `NUMERIC(14,2)` columns, `Decimal` in Python, decimal strings in JSON, `decimal.js` in the browser, rounding half-up to cents | rounding tests in `test_compensation.py`, `compensation.test.ts` |
| **Data integrity** | One transaction per salary change (row lock, compensation, history, audit); `CHECK` constraints; unique code and email; append-only trigger on history | `test_compensation.py` (rollback and trigger tests) |
| **Performance at 10,000 rows** | Search, filter, sort, pagination and all aggregates run in PostgreSQL; indexed filter columns; constant query count per list request | N+1 guard test; timings in [testing-and-performance.md](testing-and-performance.md) |
| **Serverless suitability** | Stateless JWT auth, no sessions, background jobs or local files; `NullPool` and no prepared statements behind Neon's pooler; migrations and seeding run outside requests | `app/db/engine.py`, `app/db/session.py`, `tests/test_engine.py` |
| **Security** | bcrypt hashes, signed JWT, secrets only from environment variables, CORS allow-list, validation on client and server, API docs off in production | `app/core/`, `tests/test_auth.py` (CORS, expiry, forged token) |
| **Usability** | Loading, empty and error states on every data view; confirmation before salary changes and termination; Tailwind responsive layout | component tests; the layout has not been device-tested by the author |
| **Maintainability / testability** | Layered backend (routes, services, repositories, models); tests run on a real PostgreSQL | 138 backend and 50 frontend tests |

## 4. Scope and deliberate exclusions

**In scope:** everything in section 2.

**Excluded, and why**

| Excluded | Reason |
|---|---|
| LLM / AI features, LangChain, vector databases | Explicitly ruled out by the brief; no requirement needs them |
| Redis, Celery, background workers, microservices | Ruled out by the brief; the serverless target has no long-running processes |
| Live exchange-rate API | The brief asks for no paid external API; rates are entered by HR and stored with a date and source |
| Roles, permissions, SSO, user-management UI | One persona; users are created by the seed script. Any authenticated, active user can use every protected endpoint |
| Currencies other than INR / USD / EUR | The specified scope; adding one needs a constant and a migration |
| Hard-deleting employees | Pay history must be retained; employees are marked `terminated` instead, which freezes their pay |
| Payroll, tax, benefits, bonuses, equity | This is a compensation record and analytics system |
| Bulk import or export through the UI | Bulk loading is a standalone script by design |

## 5. Assumptions made (documented, not requirements)
- Only INR, USD and EUR are supported, so seeded UK payroll is in EUR and Singapore and Canada are in USD.
- Pay of different frequencies is compared as annual-equivalent (monthly × 12, hourly × 2,080 hours).
- Analytics on pay cover employees who have compensation and are not terminated; headcount charts include everyone.
- The latest exchange rate on or before today is used for conversion, not the rate in force when a salary was set.
