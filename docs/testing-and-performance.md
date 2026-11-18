# Testing and Performance

Everything below was run or measured during development (final verification on 18 Nov 2026). Commands to reproduce are in README section 15. Nothing here is a formal benchmark.

## 1. Test approach

**Backend (pytest, `backend/tests/`) runs against a real PostgreSQL**, not SQLite, because the behaviours worth testing are PostgreSQL-specific: the append-only trigger, `percentile_cont`, row locks, `NUMERIC` and `CHECK` constraints. The suite starts an embedded PostgreSQL (`pgserver`) or uses `TEST_DATABASE_URL`. It refuses to run if the URL is a `.neon.tech` host, because it truncates tables between tests. Tests drive the real FastAPI app through `TestClient` and read back the database to assert side effects (history rows, audit rows, rollbacks).

**Frontend (Vitest + React Testing Library)** tests behaviour through the DOM with the API layer mocked: what is rendered, what the user can do, and which API call results.

**Not tested automatically:** browser end-to-end flows (no browser-automation tool is part of the project), mobile/responsive layout, concurrent salary changes, load, and Docker Compose.

## 2. Results

| Check | Result |
|---|---|
| Backend: `python -m pytest` | **138 passed** (about 80 s) |
| Frontend: `npm test` | **50 passed** in 7 files (about 12 s) |
| TypeScript: `npm run typecheck` (`tsc -b --noEmit`) | passes |
| Production build: `npm run build` | succeeds; also run from a **fresh clone** of the repository with `npm ci` (what Vercel does) |
| Neon database right after migration and seed | revision `0001`, no drift (`alembic check`); **as seeded:** 10,000 employees, 10,000 compensation rows, 23,225 history rows; re-running the seed inserts 0 |
| Deployed apps (18 Nov 2026) | frontend returned HTTP 200; backend `/health` and `/health?deep=true` returned `{"status":"ok"}` |

### Backend tests by file
| File | Tests | Covers |
|---|---|---|
| `test_employees.py` | 24 | create, get, update, duplicate email/code, invalid input matrix, manager rules, atomic create |
| `test_search.py` | 22 | search by name/ID/email, wildcard escaping, every filter, combined filters, salary range with conversion and exact boundary inclusion, sorting, pagination, invalid parameters, constant query count (N+1 guard) |
| `test_compensation.py` | 29 | percentage and fixed increments, rounding, history rows, effective-date and negative-result rules, terminated freeze, currency/frequency change, rollback on failure, immutability trigger, DB constraints, history ordering |
| `test_currency.py` | 18 | direct / inverse / triangulated rates, missing rate, rounding, as-of snapshot, rate API validation, conversion endpoint, no mutation of stored salaries |
| `test_analytics.py` | 11 | counts, per-currency totals, average / median / min / max, department and country stats, bands, trends, recent changes, missing-rate error |
| `test_auth.py` | 15 | bcrypt, login, bad credentials, protected endpoints, expired and forged tokens, inactive user, health, CORS |
| `test_seed.py` | 6 | determinism, unique codes and emails, arithmetically consistent history, variety, re-runnable insert, valid managers |
| `test_pg8000_driver.py` | 5 | analytics, directory search and trends through the fallback pg8000 driver; rate precision; exact boundary |
| `test_engine.py` | 6 | pooler detection, driver-specific connection options, URL normalisation |
| `test_smoke.py` | 2 | health, create-and-get |

### Frontend tests by file
| File | Tests | Covers |
|---|---|---|
| `EmployeeDirectory.test.tsx` | 11 | rendering, loading / error (with retry) / empty states, debounced search, filters, salary range, clear-all, sorting, pagination, page size |
| `validation.test.ts` | 17 | employee, increment and compensation form rules |
| `compensation.test.ts` | 5 | increment maths (the brief's 10% example), rounding, invalid input |
| `IncrementDialog.test.tsx` | 5 | live preview, fixed amount, validation, review-then-confirm, server errors |
| `EmployeeForm.test.tsx` | 5 | validation messages, server error mapping, submitted payload |
| `api.test.ts` | 4 | production API-URL guard, query-string building |
| `PasswordInput.test.tsx` | 3 | show/hide toggle |

## 3. Defects that verification found (and the tests added)
| Defect | How it was found | Fix and test |
|---|---|---|
| Currency conversion rounded half-even | unit test | half-up rounding |
| `PATCH` returned the unnormalised amount (`7000` not `7000.00`) | API test | refresh the row after commit |
| `/analytics/trends` failed under the pg8000 driver (GROUP BY expression differed because the format literal was a separate parameter) | live check against Neon data | group by output position; `test_pg8000_driver.py` fails without the fix |
| Exchange rates rounded to 2 decimals under pg8000 (INR→USD used 0.01 instead of 0.012012…), so converted totals were wrong | a screenshot of the Analytics table (₹5,873,980,049.75 shown as $58,739,800.50) | rate bound as `NUMERIC(38,20)`; regression test |
| Salary-range filter dropped employees exactly on a boundary (EUR 46,000 = USD 50,000) | cross-check of the API against exact-fraction arithmetic | exact `num ÷ den` conversion; tests on both drivers |
| `frontend/src/lib/` was never committed (a generic Python `.gitignore` rule ignored `lib/`), so the Vercel build failed | the failed Vercel build; reproduced from a fresh checkout | ignore rule anchored; files committed; clean-clone build verified |

## 4. Data scale and seed data
- **10,000 employees**, 10,000 compensation rows, 23,225 salary-history rows, 6 countries, 10 departments, 70 designations (7 levels per department), in INR (3,391 employees), USD (4,206) and EUR (2,403). Statuses: 9,084 active, 414 on leave, 502 terminated. Frequencies: 6,762 annual, 2,795 monthly, 443 hourly. Names and data are fictional.
- Generated by `backend/seed` with a fixed seed; the same counts were produced locally and on Neon.
- These are the **as-seeded** figures. The live demo database is in use, so its counts drift (at the time of writing it held 10,001 employees and 23,227 history rows).
- Seed time observed: about 23 s for an early local run (before inserts were batched) and about 76 s to Neon over the internet (batched).

## 5. Pagination, filtering, sorting and query design
- Search, filters, sort and pagination execute in PostgreSQL; the browser holds one page. Page size is limited to 100.
- The list query is one `SELECT` with the compensation outer-joined and country/department eager-loaded, plus one `COUNT`. A test asserts the number of SQL statements does not grow with page size.
- Filter columns are indexed (department, country, status, designation, joining date); name search is `ILIKE` and does not use an index; sorting by salary orders by a computed expression, also not indexed. At 10,000 rows these are scans of a small table.
- Aggregates (`AVG`, `percentile_cont`, `MIN`, `MAX`, `SUM`, counts) are computed in the database and the response includes the rate date used.

## 6. Observed timings (single user, ad hoc, not benchmarks)
| Environment | Observation |
|---|---|
| Local embedded PostgreSQL, API on the same machine | directory page 36–91 ms (list 56, search 78–91, filtered + salary sort 36, last page 81); dashboard about 180–200 ms; each analytics endpoint 26–71 ms |
| Neon (Singapore region) from the development machine over the internet, via the pg8000 driver | first requests 1.7–3.8 s (directory page 2.2 s, search 1.8 s, dashboard 3.8 s); dominated by network round trips |

The deployed Vercel-to-Neon latency was not measured. No load, concurrency or soak tests were run.

## 7. Limitations and possible improvements (not implemented)
- Add a `pg_trgm` index if the employee table grows by orders of magnitude; use keyset pagination for deep pages.
- Index or precompute the annualised, converted salary if salary sorting must scale; cache dashboard aggregates.
- Test the row-lock behaviour under concurrent salary changes; add load testing.
- Add browser end-to-end tests and device testing of the responsive layout.
- Run and verify the Docker Compose setup (Docker was unavailable during development).
- Use each salary's historical exchange rate for analytics, if the business needs it.
