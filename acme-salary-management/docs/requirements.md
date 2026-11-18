# Requirements: ACME Salary Management System

## Product goal
Replace ACME's Excel-based salary tracking with one web application where HR can find any of ~10,000 employees in seconds, change pay with a full audit trail, and see how the organisation pays its people, across countries and currencies.

## User persona
**HR Manager** (single role). Works in a browser, manages employee records and compensation, answers questions like "what is our median engineering salary in Germany compared with India?", needs confidence that pay history is never silently altered.

## Functional scope
| Module | Capability |
|---|---|
| Dashboard | Headcount (total, active, by country/department/status); pay totals per original currency; average/median/min/max; salary bands; recent salary changes; reporting-currency selector (INR/USD/EUR). |
| Employee directory | Server-side search (name, employee ID, email), filters (department, country, designation, status, salary range), sorting (name, joining date, salary), pagination with configurable page size, clear-all, loading/empty/error states. |
| Employee profile | All profile fields, manager, current compensation, salary history; create, edit, terminate (with confirmation). |
| Compensation | Add compensation, update salary/currency/frequency, fixed and percentage increments, effective date, reason, live preview and confirmation step. |
| Salary history | Immutable, chronological ledger of every change with who/when/why. |
| Analytics | Average and median by department, distribution by country and department, headcount by salary band, trends over time, breakdown by currency; all cross-currency numbers converted. |
| Currency | INR, USD, EUR; original salary is always stored in its own currency; exchange rates stored in the database and maintained by HR; the rate date used is displayed. |
| Authentication | HR login (JWT), all APIs protected. |

## Non-functional requirements
- **Correctness of money:** `NUMERIC`/`Decimal` end to end; no floats in storage or calculation.
- **Integrity:** salary change + history row + audit row commit atomically; history cannot be updated or deleted.
- **Performance:** directory/search/analytics queries run in the database; every request < ~250 ms on 10,000 employees (measured, see README).
- **Deployability:** stateless short-lived requests suitable for Vercel Python Functions + Neon; migrations and seeding run outside request handling.
- **Security:** bcrypt password hashes, secrets only from environment, CORS allow-list, input validated on both client and server.
- **Usability:** responsive, accessible (labels, `aria-invalid`, live regions), consistent loading/empty/error states.
- **Testability:** automated backend tests against real PostgreSQL; frontend tests for core flows.

## Explicit exclusions (and why)
| Excluded | Reason |
|---|---|
| LLM / AI features, vector DB, LangChain | Not needed for the problem; adds cost and risk. |
| Redis, Celery, background workers, microservices | Serverless target has no long-running processes; no workload needs them. |
| Live exchange-rate API | Paid/unreliable dependency; HR-controlled manual rates are auditable and sufficient. |
| Multi-role RBAC, SSO, user-management UI | Single persona for this assessment; users are created by the seed script. |
| Payroll processing, tax, benefits, bonuses/equity | Out of scope: this is a compensation *record* and analytics system. |
| Currencies beyond INR/USD/EUR | Specified scope; adding one is a data + constant change. |
| Hard-deleting employees | HR records need retention; employees are terminated instead. |
| Bulk import/export through the UI | Bulk load is a standalone seed script by design. |
