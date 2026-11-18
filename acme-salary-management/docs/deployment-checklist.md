# Deployment checklist

Tick each box only after you have actually done and observed it. Replace `<backend>` and `<frontend>` with your Vercel URLs. Background and settings: README section 18.

Status: items marked ✅ were observed by the author on 2026-11-18 (database work, and reachability/health of the deployed frontend and backend). The browser-level checks in sections C–E and the final demo are for the product owner to tick.

## A. Database (Neon)
- [x] ✅ Neon database created (pooled and direct connection strings available)
- [x] ✅ `backend/.env` contains `DATABASE_URL` (pooled) and `DATABASE_URL_DIRECT` (direct); `.env` is git-ignored
- [x] ✅ Migrations executed: `python -m alembic upgrade head` → `python -m alembic current` shows `0001 (head)`; `python -m alembic check` reports no drift
- [x] ✅ 10,000 employee records verified: `select count(*) from employees;` = `10000` (also 10,000 compensation rows, 23,225 history rows, 1 user, 2 exchange rates)
- [x] ✅ Re-running `python -m seed.run` inserts 0 rows (idempotent)
- [ ] Neon password rotated if it was ever shared outside `.env`, and `.env` / Vercel updated

## B. Backend (Vercel project, Root Directory `acme-salary-management/backend`)
- [ ] Project created; Root Directory set; Python 3.12 (from `.python-version`)
- [ ] Env vars set: `DATABASE_URL` (pooled), `JWT_SECRET`, `CORS_ORIGINS`, `APP_ENV=production`
- [ ] First build log shows dependencies installed from `pyproject.toml` and the FastAPI entrypoint detected (`app/main.py`)
- [x] ✅ Backend deployed (`https://acme-salary-api.vercel.app`)
- [x] ✅ `curl https://<backend>/health` → `{"status":"ok"}` (observed 2026-11-18)
- [x] ✅ `curl "https://<backend>/health?deep=true"` → `{"status":"ok"}` (proves the Neon connection; observed 2026-11-18)
- [ ] `https://<backend>/docs` is **not** available (production)

## C. Frontend (Vercel project, Root Directory `acme-salary-management/frontend`)
- [ ] Project created; preset Vite; build `npm run build`, output `dist`
- [ ] `VITE_API_BASE_URL=https://<backend>` set **before** the build
- [x] ✅ Frontend deployed (`https://salary-management-system-theta.vercel.app/` returned HTTP 200 on 2026-11-18)
- [ ] Deep link works (open `https://<frontend>/employees` directly and refresh; no 404)
- [ ] Frontend connected to backend (login page can reach the API; no "not configured" message)

## D. Cross-origin and security
- [ ] `CORS_ORIGINS` on the backend contains exactly `https://<frontend>` (no trailing slash); backend redeployed
- [ ] CORS verified: `curl -i -X OPTIONS https://<backend>/api/v1/auth/login -H "Origin: https://<frontend>" -H "Access-Control-Request-Method: POST"` returns `access-control-allow-origin: https://<frontend>`
- [ ] A foreign origin is rejected (same command with `Origin: https://example.com` returns 400)
- [ ] No secrets in the repo: `git ls-files | grep -i "\.env$"` prints nothing

## E. Functional verification on production
- [ ] Authentication verified: sign in with the seeded HR account; wrong password is rejected; signing out returns to login
- [ ] Employee directory: search (name, ID, email), filters, sort (name / joining date / salary), pagination and page size work
- [ ] Employee CRUD verified: create an employee ("Demo Tester"), view the profile, edit a field, terminate it (confirmation shown)
- [ ] Salary increment verified: INR 1,500,000 + 10% → INR 1,650,000 (increment 150,000); fixed +50,000 → INR 1,700,000
- [ ] Salary history verified: both changes listed with previous → new amount, %, effective date, reason and HR user
- [ ] Terminated employee: increment / update disabled, history preserved
- [ ] Currency conversion verified: switch reporting currency USD → INR → EUR; values change, rate date note is shown, stored salaries stay in original currency; adding a rate in Settings works
- [ ] Dashboard analytics verified: totals, by-country / department / status, bands, recent changes match the data
- [ ] Analytics page verified: department and country comparisons, distribution, both trend charts, currency breakdown (no error cards)

## F. Quality gates (run from your machine before submitting)
- [ ] `cd backend && python -m pytest` passes
- [ ] `cd frontend && npm test` passes
- [ ] `cd frontend && npm run typecheck` passes
- [ ] Production build verified: `cd frontend && npm run build` succeeds
- [ ] `git status` is clean; history is the original incremental commits
- [ ] Docker Compose run end to end *(optional; not verified by the author because Docker was unavailable)*

## G. Submission
- [ ] README reviewed; links in `docs/` work
- [ ] Final demo recorded (login → directory → profile → increment → history → currency switch → dashboard → analytics)
- [ ] Repository URL, deployed frontend URL and demo link shared
