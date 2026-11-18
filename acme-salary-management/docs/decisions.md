# Engineering decisions and trade-offs

| # | Decision | Why | Trade-off / revisit when |
|---|---|---|---|
| 1 | **Current pay (`compensation`) and history (`salary_history`) are separate tables** | Simple fast reads of current pay; history can be append-only. | Two writes per change, hence one transaction. |
| 2 | **Money is `NUMERIC` + `Decimal` everywhere; API sends decimals as strings; client uses `decimal.js`** | No float rounding errors; ROUND_HALF_UP to cents identical on client and server. | Strings need parsing for display only. |
| 3 | **History immutability enforced by a DB trigger**, not just app code | Holds even against ad-hoc SQL or future code. | Trigger is PostgreSQL-specific; tests therefore run on real PostgreSQL. |
| 4 | **Row lock (`FOR UPDATE`) during a salary change** | Two HR users incrementing simultaneously can't lose an update. | Short lock per employee only. |
| 5 | **Effective date can't precede the current effective date; terminated employees' pay is frozen** | Keeps the ledger monotonic and meaningful. | Retroactive corrections would need a dedicated "correction" flow. |
| 6 | **Original currency stored; conversion at read time** from `exchange_rates` (direct → inverse → USD triangulation) | Never mutates source data; rates can be corrected/added without rewriting salaries; the rate date is shown. | Analytics use the *latest* rate, not each salary's historical rate. |
| 7 | **Exchange rates are manual (Settings page / seed)** | No paid API dependency; auditable. | Rates can go stale; a scheduled job could later insert rows. |
| 8 | **Supported-currency set is a CHECK constraint + constants** | Strong validation at every layer. | Adding a currency = migration + constant. |
| 9 | **UK payroll in EUR; Singapore/Canada in USD** | Only INR/USD/EUR are in scope but six countries are required. Documented assumption in seed data. | Not realistic for UK/SG/CA; add GBP/SGD/CAD to remove. |
| 10 | **Hourly = 2,080 h/year; annual comparison basis** | Needed to compare hourly/monthly/annual pay. | Fixed assumption; make configurable if needed. |
| 11 | **Analytics population = employees with pay and status ≠ terminated** | Terminated people shouldn't skew "how we pay today". Headcount charts include everyone. | Stated on the pages. |
| 12 | **Medians/percentiles via `percentile_cont`** (float8) then rounded to cents | Exact, in-database, fast. | Derived statistics only; never stored or used for transactions. |
| 13 | **Search is `ILIKE` over name/code/email, B-tree indexes on filter columns** | Fast enough at 10k (≈50–90 ms measured); no extension needed (works on Neon and embedded PG). | At 1M+ rows add `pg_trgm` GIN. |
| 14 | **Offset pagination** (`LIMIT/OFFSET`, stable `id` tie-break) | Page numbers + jump-to-page are required UX. | Deep offsets get slower; keyset would be needed at very large scale. |
| 15 | **Sync SQLAlchemy + psycopg 3** | Simpler, correct, and ideal for short-lived serverless requests. | Async adds complexity without benefit here. |
| 16 | **`NullPool` + `prepare_threshold=None` when `APP_ENV=production`** | Neon's PgBouncer owns pooling; avoids stale connections and prepared-statement errors. | Slightly slower per request than a warm pool. |
| 17 | **JWT (HS256) in `localStorage`, bearer header, no cookies** | Stateless, works across two Vercel domains without CSRF/cookie-domain trouble. | XSS exposure of the token; mitigated by no HTML injection paths and short expiry. A BFF with HttpOnly cookies is the hardening step. |
| 18 | **No login rate-limiting** | Needs shared state (Redis/DB) — outside scope. | Put Vercel Firewall/WAF rate limits in front for real use. |
| 19 | **Users are created by the seed script only** | Single persona; avoids a user-management surface. | Add an admin CLI/UI for more users. |
| 20 | **Seed generation is separate from DB code** (`generator.py` is pure) and **idempotent** (skip by code/email), single transaction | Deterministic, testable, safe to re-run, all-or-nothing. | Re-running never *updates* existing rows. |
| 21 | **Backend tests run on real PostgreSQL** (embedded `pgserver` or `TEST_DATABASE_URL`) | Triggers, `percentile_cont`, locks and NUMERIC behaviour are the things worth testing. | Slightly slower than SQLite. |
| 22 | **Consistent error envelope** `{"error": {code, message, details[]}}` | Frontend maps `details[].field` straight onto form fields. | — |
| 23 | **Two-step confirmation for salary changes** (form → review → confirm), terminate needs confirm | Salary changes are permanent in the ledger. | One extra click. |
| 24 | **Chart colours from a validated colour-blind-safe palette**; single series use one hue; paired series (average/median) use two adjacent slots with a legend | Accessibility. | — |
