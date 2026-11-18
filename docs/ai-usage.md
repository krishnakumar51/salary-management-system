# AI Usage

This project was built with an AI coding assistant. This page states plainly what the AI did, what the human owner did, and how the output was checked. Evidence is the Git history and the project's test and verification records.

## 1. Tools
- **Claude Code** (Anthropic's coding agent) running in VS Code, model **Claude Sonnet 5.5**. It read and wrote files, ran commands (tests, builds, migrations, the seed script, API checks) and committed to Git in the owner's environment.
- **Git evidence:** all 14 commits are authored under the owner's Git identity. 12 carry a `Co-Authored-By: Claude Sonnet 5.5` trailer. The other two are GitHub's initial commit and the owner's own "updated readme" commit.

## 2. What the AI did
Working from the assessment brief supplied by the owner, the AI produced essentially all of the repository content:

| Area | Examples |
|---|---|
| Architecture and design | layered backend, two-table pay/history model, currency strategy, deployment layout |
| Backend | FastAPI routes, services, repositories, SQLAlchemy models, Alembic migration (including the append-only trigger), JWT/bcrypt auth, error envelope |
| Frontend | React pages, forms and dialogs, charts, API client, validation, increment preview |
| Data | the deterministic 10,000-employee seed generator and its runner |
| Tests | 138 backend and 50 frontend tests |
| Configuration | Docker, Compose, Vercel, environment templates, the Neon pooled/direct URL support |
| Documentation | READMEs and everything under both `docs/` folders, written from inspecting the code |
| Debugging | reproducing and root-causing the defects listed below |

## 3. What the human owner did
Based on what the project record shows:
- **Defined the product and constraints:** the assessment brief (stack, modules, currency rules, exclusions such as no LLM, Redis or paid FX API) and the safety rules for the Neon work (verify the target database first, no destructive operations).
- **Provided and operated the infrastructure:** created the Neon database and supplied its connection string, created the two Vercel projects, deployed, and supplied the live URLs and the Loom demonstration.
- **Ran the application and reported what was wrong**, usually with screenshots or error output: login failing because the frontend pointed at another service on port 8000; a CORS failure from the dev server on port 3000; the Analytics page showing a failed trends chart and wrongly converted totals; a red TypeScript error in the editor; the failing Vercel build.
- **Directed the work:** asked for the show/hide password control and the login heading, asked the AI to stop browser automation and rely on tests and backend verification, and requested the example scenarios to check by hand.
- **Chose what to publish:** the demo account and its labelling.

## 4. How the AI's output was checked
- **Automated tests** written alongside the code (138 backend on real PostgreSQL, 50 frontend), re-run before each hand-off.
- **Independent cross-checks:** the API's sorting, filters, search and pagination were compared with direct SQL and exact-fraction arithmetic on the Neon data (29 checks); write flows (increment, update, currency change, termination) were exercised end to end on a local copy so production data was not altered.
- **Clean-clone build:** the frontend was built from a fresh checkout, which is how the missing-files problem was reproduced and the fix proven.
- **Static checks:** link checks across the Markdown, and secret scans of the working tree and the full Git history.
- **Live checks:** the deployed frontend and the backend `/health` and `/health?deep=true`.
- **Owner's use of the UI:** the owner exercised the running application in a browser. The AI made one early browser render of the dashboard and then stopped at the owner's request.

## 5. AI-generated defects that this process caught
The AI's code was not correct on first generation. Details, with the regression tests, are in [testing-and-performance.md](testing-and-performance.md#3-defects-that-verification-found-and-the-tests-added). In summary: half-even instead of half-up rounding; an unnormalised amount in an API response; an analytics query that failed on the pg8000 driver; exchange rates rounded to two decimals under pg8000, which produced wrong converted totals (noticed by the owner from a screenshot); salary-range filters that dropped employees exactly on a boundary; a `.gitignore` rule that kept `frontend/src/lib/` out of Git and broke the Vercel build; and a test-harness mistake in the AI's own test. Each was found by a test, a cross-check, the owner's use of the app, or a failed build, not by the AI at generation time.

## 6. Limits of this statement
- The repository contains no record of a line-by-line human review of every file. Treat the code as **AI-generated and test-verified**, and rely on the tests and the verification described above.
- UI quality was judged mainly by the owner's manual use; there is no automated browser test suite.
- Docker Compose was written but never run, and concurrency behaviour of the salary-change lock was not tested.
