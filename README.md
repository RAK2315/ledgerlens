# LedgerLens

GST reconciliation for Indian businesses. LedgerLens checks one month of invoices against the ledger, the bank statement and GSTR-2B, prices every mismatch in rupees, explains it with evidence and drafts the fix for approval.

Built for Fintechstico V7.0 (NSUT Consilium'26), problem statement 2.

## What is in this repo

| Folder | What it holds |
|---|---|
| ml | Data loading, GSTR-2B generation, the two trained matchers (invoice to ledger, invoice to bank) |
| backend | FastAPI app: the rules engine, the money maths, the SQLite store, Drafts |
| frontend | Next.js app: landing page, dashboard, workbench, ring view, liability, proof, data |
| docs | The demo script for the video and the live presentation |
| data | The dataset and the generated GSTR-2B lines |
| plan, CONTEXT.md, ML_BUILD.md | The design documents |
| deck | The ideathon deck |

## Run it on a laptop (Windows)

Needs Python 3.10, Node 20 or newer and pnpm.

One time:

```
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python -m pip install -e ml
pnpm --dir frontend install
pnpm --dir frontend build
cd backend
.venv\Scripts\python -m app.warm
cd ..
```

The last step loads the demo data and runs the analysis once (about 30 seconds), so the app is fast afterwards.

Every time: double-click start.cmd. It starts the API on port 8000 and the web app on port 3000 and opens the browser.

Drafts are worded by a language model through Groq. Put the key in backend/.env as GROQ_API_KEY=... and LLM_MODE=live. Without a key the app uses the cached Drafts in backend/cache/drafts and plain templates. The demo month is already cached, so it runs with no network.

## Tests

```
ml\.venv\Scripts\python -m pytest ml\tests -q
backend\.venv\Scripts\python -m pytest backend\tests -q
pnpm --dir frontend typecheck
pnpm --dir frontend lint
backend\.venv\Scripts\python backend\scripts\check_engine.py
```

The last command prints how many planted errors the engine catches, per Finding type, over the whole year.

## Put it online (optional)

Backend, on any host that runs a Dockerfile (render.yaml is a ready blueprint for Render):

1. Create a web service from this repo. It builds the Dockerfile at the repo root.
2. Set CORS_ORIGIN to the frontend URL. Set GROQ_API_KEY and LLM_MODE=live only if new Drafts should be written online.

Frontend, on Vercel:

1. Import the repo and set the root directory to frontend.
2. Set NEXT_PUBLIC_API_URL to the backend URL.

The backend keeps its database on the container's disk, so approvals reset when the service restarts. That is fine for a demo.

## Hosted copy

- Backend: a Hugging Face Docker Space at https://rak2315-ledgerlens-api.hf.space (health check at /api/health). It is public, allows calls from any site and serves only the demo data. To update it, commit, then run `python deploy/hf-space/push.py` from the repo root while logged in with `hf auth login`. Only files tracked by git are sent.
- Frontend: Vercel, root directory `frontend`, with `NEXT_PUBLIC_API_URL` set to the Space URL. The value is fixed at build time, so redeploy after changing it.
- A free Space sleeps when idle. Open the health check a few minutes before showing the hosted copy.
