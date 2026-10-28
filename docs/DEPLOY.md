# Publishing to GitHub and deploying for free

Nothing in this file has been done yet. Each step below is an action **you**
take, under your own GitHub account. No step costs money or needs a card.

| | |
|---|---|
| Code host | GitHub, public repository (free) |
| App host | Streamlit Community Cloud — free, unlimited public apps, no card |
| Docs host (optional) | GitHub Pages can serve the docs as static pages. It **cannot** run the dashboard: Pages serves files only, and the dashboard is a Python server. |

## Deployment settings — exact values

| Setting | Value |
|---|---|
| Repository | `<your-github-username>/mandimitra` (public) |
| Branch | `main` |
| Main file path | `app.py` |
| Python version (Advanced settings) | **3.12 — set it explicitly.** Do not accept the default: on 28 Oct 2026 the default was Python 3.14, and the build failed (no pre-built wheels for the pinned pandas/numpy/lxml, so it tried to compile them). 3.11 also works. Anything 3.13 or newer fails. The version cannot be changed later without deleting and redeploying the app. |
| Dependencies | `requirements.txt` at the repo root (Community Cloud installs it automatically) |
| Secrets | **None.** The app uses no keys, tokens or accounts. Leave the Secrets box empty. |
| Data | Committed in the repo: `data/raw/source/`, `data/raw/*.csv`, `data/interim/clean.parquet`, `data/processed/features.parquet`, `outputs/**`. The app reads them; it trains nothing at start-up. |
| Resource limits | Up to 2.7 GB RAM per app; the app uses a small fraction. Sleeps after 12 hours without visitors and wakes when someone next opens it (after a short wait). |

## Step 1 — check locally (2 minutes)

```bash
cd ~/Downloads/mandi-price-forecast
source .venv/bin/activate
python -m pytest                     # expect: all passed
```

## Step 2 — create the local repository

```bash
cd ~/Downloads/mandi-price-forecast
git init -b main
git add -A
git status --short | wc -l           # expect about 90 files
git status --short | grep -E "\.venv|_to_delete|\.bak|\.DS_Store|secrets" \
  && echo "STOP: something private is staged" || echo "clean"
git commit -m "MandiMitra: explainable mandi price evaluation"
```

The `.gitignore` already excludes the virtual environment, caches, backups,
`_to_delete/`, `.DS_Store`, and any `.env` or Streamlit secrets file.

## Step 3 — create the GitHub repository and push

Either on github.com (**New repository** → name `mandimitra` → Public → do
**not** add a README, licence or .gitignore → Create), then:

```bash
git remote add origin https://github.com/<your-github-username>/mandimitra.git
git push -u origin main
```

or, with the GitHub CLI installed and logged in (`gh auth login`):

```bash
gh repo create mandimitra --public --source=. --remote=origin --push
```

Git will ask you to sign in through your browser or credential manager. Never
paste a token into a file in this project.

## Step 4 — check CI

On GitHub, open **Actions**. The **CI** workflow runs the tests on Python 3.11
and 3.12, rebuilds every result from the government files, checks the rebuild
matches the committed results, and starts the app. Expect a green tick in about
5–10 minutes. If it is red, fix that before deploying.

## Step 5 — deploy

1. Go to <https://share.streamlit.io/> and sign in with GitHub.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repository `<your-github-username>/mandimitra`, branch `main`, main file
   `app.py`.
4. Optional App URL, e.g. `mandimitra` → `https://mandimitra.streamlit.app`
   (if free).
5. **Advanced settings** → Python version **3.12** → no secrets → Save.
6. **Deploy**. The first build takes a few minutes.

## Step 6 — smoke test the live URL (do all of these)

| Check | Expected |
|---|---|
| Page loads | **MandiMitra** title and the amber *Historical data… ends on 28 Apr 2015* banner |
| Overview, Onion/Jaipur | Last reported Rs. 550 · 56% · Beats "same as today"? No · three forecasts of Rs. 550 |
| Switch to Tomato | Last reported Rs. 1,500; forecasts Rs. 1,484 / 1,508 / 1,502 |
| Model evaluation, 1 / 2 / 3 days | Timeline, table, fold chart, and the **Actual vs predicted** chart with two models pre-selected |
| Forecast tab | Made on 28 Apr 2015, for 29 Apr – 1 May 2015 |
| हिन्दी | Header and overview switch to Hindi |
| Phone | Opens and scrolls without sideways scrolling |
| Logs (**Manage app**) | No traceback |

Only after every row passes, add the link to the README's *Live demo* line.

## If something goes wrong

| Symptom | Fix |
|---|---|
| Build fails on numpy / scipy / lxml / pandas ("Failed to build", "libxml2 and libxslt development packages") | Python version is not 3.11 or 3.12 — check the line `Using Python 3.x` at the top of the logs. Delete the app and redeploy with 3.12 under Advanced settings. |
| "The data has not been built yet" | `data/processed/features.parquet` or `outputs/` was not pushed. `git ls-files outputs data | head` must list them. |
| App is slow to open | It was asleep; wait for it to wake. Open it yourself shortly before anyone else needs it. |
| A bad change went live | `git revert <commit>` then `git push` — the app redeploys from `main` automatically. Or, in **Manage app**, reboot. |
| Need to take it down | Workspace → app menu → **Delete**. The repository is unaffected. |

## Recovery and rollback

Every deploy is a git commit, so any earlier state can be restored with
`git revert` (safe, keeps history) and a push. The local app does not depend on
the hosted one — for a live demo, always run it locally.
