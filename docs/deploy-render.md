# Deploy EduIntel to a live URL (GitHub → Render)

This makes EduIntel a permanent, public link. It deploys as **one web service**
(the FastAPI backend serves both the API and the built React app) plus a
**managed PostgreSQL** database with pgvector. Everything is pre-configured in
[`render.yaml`](../render.yaml) and [`deploy/Dockerfile`](../deploy/Dockerfile).

> Free tier note: the free web service **sleeps after ~15 min idle** (first visit
> then takes ~30s to wake) and has 512 MB RAM. That's fine for a portfolio link.
> For always-on, pick the paid Starter instance in Render.

## 1. Push the project to GitHub

Install **Git** (git-scm.com) and create a free **GitHub** account, then:

1. On github.com → **New repository** → name it `eduintel` → **Create** (don't add a README).
2. Extract the project zip if you haven't. Open a terminal **in the `EduIntel` folder** and run:

```bash
git init
git add .
git commit -m "EduIntel — AI education intelligence platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/eduintel.git
git push -u origin main
```

(When prompted to log in, use your GitHub username + a **Personal Access Token**
as the password — GitHub → Settings → Developer settings → Tokens.)

Your secrets are safe: `.env` is gitignored, so your Gemini key is **not** pushed.

## 2. Deploy on Render

1. Create a free account at **render.com** and click **New → Blueprint**.
2. **Connect your GitHub** and pick the `eduintel` repo. Render reads `render.yaml`
   and shows a web service **eduintel** + a database **eduintel-db**.
3. Click **Apply**. When asked, paste your **GEMINI_API_KEY** (optional — leave
   blank and the app still works with its offline fallback).
4. Wait for the build (~5–10 min the first time). On first boot the service
   **seeds demo data and trains the model automatically** (~1 min).
5. Open the service URL Render gives you (e.g. `https://eduintel.onrender.com`).
   That's your live link. 🎉

## 3. If the dashboard is empty after deploy

That means first-boot seeding ran out of memory on the free instance. Fix any one:

- In the service's **Environment**, set `EDUINTEL_SEED_STUDENTS` to `150`, then
  **Manual Deploy → Clear build cache & deploy**; **or**
- Upgrade the instance to **Starter** (more RAM) and redeploy; **or**
- Open the service **Shell** in Render and run:
  `cd /app && python scripts/bootstrap.py --fast`

## Notes

- **pgvector**: `render.yaml` provisions Postgres 16; the app enables the `vector`
  extension automatically on startup.
- **Custom domain / always-on**: configure in the Render dashboard (paid).
- **Updates**: push to `main` and Render auto-deploys (`autoDeploy: true`).
- **Alternative hosts**: the same Docker image runs on Railway, Fly.io, or any VPS
  (`docker build -f deploy/Dockerfile -t eduintel .`).
