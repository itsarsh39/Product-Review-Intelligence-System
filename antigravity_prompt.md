# PROJECT BRIEF: Blinkit Review Intelligence Engine

You are a senior analytics engineer. Build the complete project described below, end to end, in this workspace. First produce an implementation plan and wait for my approval of it. Then build in the milestones listed under "Build order", running tests and verifying each milestone before moving on.

---

## 1. Goal and business framing

This is a portfolio project for a Data Analyst / Product Analytics resume. It must read as an **analytics decision project**, not an NLP demo.

**Business question:** *What are Blinkit users complaining about on Google Play, which issues cost the most rating points, and what should the product team fix first?*

The system must:
1. Ingest public Google Play reviews for Blinkit automatically and idempotently.
2. Clean the data and run automated data-quality checks.
3. Score sentiment and assign each review to one or more business themes.
4. **Validate the NLP against a hand-labeled gold set** and report the metrics honestly.
5. Estimate each theme's impact on star rating using regression and run a what-if analysis.
6. Link theme spikes to app versions and time.
7. Present everything in a Streamlit dashboard deployable on **Streamlit Community Cloud**.
8. Refresh automatically on a schedule with GitHub Actions.

**Target audience for the final dashboard:** a product manager who has 2 minutes and wants a ranked fix list.

---

## 2. Hard constraints

- **Python 3.11.** Use `pathlib`, type hints, docstrings, and `logging` (no stray `print` in library code).
- **Free tools only.** No paid APIs, no API keys required to run anything. Use local open-source models.
- **Deployment target is Streamlit only** (Streamlit Community Cloud, public GitHub repo). Do not add Power BI, Tableau, Hugging Face Spaces, or FastAPI.
- **The Streamlit app must NOT import torch, transformers, sentence-transformers, or bertopic.** Community Cloud has tight memory limits. All heavy NLP runs in the pipeline, which writes small pre-computed files to `data/processed/`. The app only reads those files.
- **Two requirements files:**
  - `requirements.txt` = app-only, lightweight (streamlit, pandas, plotly, pyarrow, etc.). Streamlit Cloud reads this one.
  - `requirements-pipeline.txt` = full pipeline (adds google-play-scraper, transformers, torch, sentence-transformers, bertopic, statsmodels, lingua-language-detector, scikit-learn, pyyaml, pytest, etc.).
  - Pin versions that are compatible with each other. Verify by installing them in a fresh venv.
- **Privacy:** never store or display reviewer user names or profile images.
- **Reproducibility:** set random seeds, keep all parameters in `config.yaml`, no hard-coded paths or thresholds in code.
- **No fabricated numbers.** Any metric in the README or dashboard must be computed from the real data by code. Where a value is not yet known, the README uses a clearly marked placeholder such as `{{FILL_FROM_RESULTS}}`, or better, is auto-generated from `data/processed/metrics.json`.
- **Do not claim causation.** Use language such as "associated with" and include a limitations section.

---

## 3. Data source

- Library: `google-play-scraper`
- App ID: `com.grofers.customerapp` (Blinkit). Verify this ID is correct before the full pull. If the ID returns no reviews, stop and ask me.
- Locale: `lang="en"`, `country="in"`
- Sort newest first. First run backfills up to `max_reviews` (default 50,000); later runs are incremental (stop when a whole batch is already stored).

**If `src/ingest.py` already exists in the workspace, keep it and build around it.** Otherwise implement it to match this spec:

SQLite database `data/reviews.db`, table `reviews`:

| column | type | note |
|---|---|---|
| review_id | TEXT PRIMARY KEY | dedupe key |
| app_id | TEXT | |
| content | TEXT | raw review text |
| rating | INTEGER | 1-5 |
| thumbs_up | INTEGER | |
| app_version | TEXT | review-created version, fall back to app version |
| reviewed_at | TEXT | ISO timestamp |
| reply_text | TEXT | developer reply |
| ingested_at | TEXT | default CURRENT_TIMESTAMP |

Use `INSERT OR IGNORE`, batches of 200, a 1-second pause between requests, and a safety cap. Handle network errors with retries and exponential backoff.

---

## 4. Repository structure

```
blinkit-review-intelligence/
├── config.yaml
├── themes.yaml                  # theme taxonomy (see section 7)
├── requirements.txt             # app-only
├── requirements-pipeline.txt    # full pipeline
├── README.md
├── LICENSE                      # MIT
├── .gitignore
├── data/
│   ├── reviews.db               # raw (gitignored if large; see note below)
│   ├── gold/
│   │   ├── gold_template.csv    # generated sample for me to hand-label
│   │   └── gold_labeled.csv     # filled by me (not by you)
│   └── processed/               # small, COMMITTED files the app reads
│       ├── reviews_scored.parquet
│       ├── theme_summary.parquet
│       ├── theme_trend.parquet
│       ├── version_theme.parquet
│       ├── impact_results.parquet
│       ├── dq_report.json
│       └── metrics.json
├── src/
│   ├── __init__.py
│   ├── config.py                # loads config.yaml
│   ├── ingest.py
│   ├── clean.py
│   ├── quality.py               # data-quality checks
│   ├── sentiment.py
│   ├── themes.py                # theme tagging
│   ├── validate.py              # gold-set evaluation
│   ├── impact.py                # regression + what-if
│   ├── versions.py              # version / time analysis
│   ├── export.py                # writes data/processed/*
│   └── run_pipeline.py          # orchestrator with CLI flags
├── app/
│   ├── streamlit_app.py         # entry point (multipage)
│   ├── pages/
│   └── utils.py
├── notebooks/
│   ├── 01_eda.ipynb
│   └── 02_topic_discovery.ipynb # BERTopic exploration only
├── tests/
├── docs/                        # screenshots, methodology notes
└── .github/workflows/
    ├── refresh.yml
    └── tests.yml
```

**Data size note:** the raw SQLite file may be large. Gitignore `data/reviews.db`, but **commit `data/processed/`** so the deployed app works. Keep processed files small (use parquet with compression; keep review text for the explorer but cap it, for example the latest 20,000 reviews, via config). The GitHub Actions refresh job must restore the DB from a cache or artifact, or rebuild it incrementally. Choose a workable approach and document it.

---

## 5. Cleaning and data quality (`clean.py`, `quality.py`)

**Cleaning steps (all thresholds in config):**
- Drop exact duplicate review text posted by the same version on the same day (likely spam), but keep one.
- Normalize whitespace, strip control characters, and keep emojis (convert to a flag column `has_emoji`, do not delete the text).
- Drop reviews with fewer than `min_words` (default 3). Report how many were dropped.
- Detect language with `lingua-language-detector` restricted to a small set (English, Hindi, and a few others). Add a `lang` column. Analysis uses English only in v1.
- Add a `likely_hinglish` heuristic flag (Roman-script text with a configurable list of common Hindi stopwords such as "nahi", "hai", "bahut", "kya", "bakwas"). Report the share excluded. Document Hinglish as a known limitation and future work.
- Add features: `word_count`, `review_month`, `review_week`, `is_negative_rating` (rating <= 2).

**Automated data-quality checks (`dq_report.json`), each returning pass/warn/fail with the measured value:**
- Row count and date range, and the max gap in days between reviews
- Null rate per column (fail if `content` or `rating` null rate exceeds threshold)
- Rating distribution sanity (all values in 1-5)
- Daily volume anomaly detection (flag days where volume deviates more than 3 median absolute deviations)
- Share of non-English and Hinglish reviews
- Duplicate rate
- Freshness: newest review is no older than N days (configurable)

The pipeline must **fail loudly** when a check marked `fail` triggers, and the refresh workflow must not commit bad data.

---

## 6. Sentiment (`sentiment.py`)

- Default model: `cardiffnlp/twitter-roberta-base-sentiment-latest` via the transformers pipeline, CPU-friendly, batched, truncated to 256 tokens.
- Fallback: VADER (`vaderSentiment`), selectable in config for speed.
- Output columns: `sentiment_label` (negative/neutral/positive), `sentiment_score` (signed, from -1 to 1, computed as P(pos) minus P(neg)).
- **Incremental:** only score reviews that have not been scored yet (key on `review_id`), caching scores to avoid recomputation.
- Report agreement with star ratings: confusion matrix of sentiment label vs rating bucket (1-2, 3, 4-5), and list the largest mismatch groups (for example, 5-star reviews with negative text). Save a sample of mismatches for the README discussion.

---

## 7. Theme tagging (`themes.py`, `themes.yaml`)

Create a **fixed, business-meaningful taxonomy** in `themes.yaml`. Each theme has: `name`, `description`, `keywords` (list), and `seed_phrases` (example sentences). Start with roughly these themes, and refine them after seeing the discovery notebook:

1. Delivery delay / late orders
2. Missing or wrong items
3. Refund and payment-reversal problems
4. Payment failures / checkout errors
5. Product quality / freshness (damaged, expired, stale)
6. Pricing, fees, and surge/handling charges
7. Delivery partner behavior
8. App bugs / crashes / slow performance
9. Login / OTP / account issues
10. Customer support quality
11. Item unavailability / out-of-stock
12. Positive: speed and convenience
13. Positive: product range / quality
14. Other / uncategorized

**Method (hybrid, multi-label):**
- Embed each review with `sentence-transformers` (`all-MiniLM-L6-v2`) and compute cosine similarity to each theme's seed phrases.
- Combine with keyword matching (regex, word-boundary aware).
- A review gets every theme whose combined score exceeds a configurable threshold, and `Other` if none do.
- Output a boolean column `theme_<slug>` per theme, plus `primary_theme` (the highest-scoring one).
- Cache embeddings to disk so reruns are fast.

**Discovery notebook (`02_topic_discovery.ipynb`):** run BERTopic on the English negative reviews, show the topics, and document in markdown which BERTopic clusters motivated which entries in `themes.yaml`. BERTopic is for discovery and justification only. The production tagger is the hybrid method above (deterministic and cheap to run in CI).

---

## 8. Validation against a gold set (`validate.py`)  — critical for credibility

- Generate `data/gold/gold_template.csv`: a **stratified random sample of 200 English reviews** (balanced across rating levels), with columns: `review_id`, `content`, `rating`, then empty columns for `gold_sentiment` and one empty column per theme (0/1), plus a `notes` column. Seed it for reproducibility.
- **I will fill in the labels myself.** Do not label reviews and do not invent a gold set. If `gold_labeled.csv` does not exist, `validate.py` must skip gracefully, log a warning, and write `validation: "pending"` in `metrics.json`.
- When `gold_labeled.csv` exists, compute:
  - Sentiment: accuracy, macro-F1, confusion matrix
  - Per-theme precision, recall, F1, and support
  - Micro and macro averages
  - A short "error analysis" table of the 20 worst misclassifications
- Save results to `metrics.json` and `docs/validation_report.md`.
- Provide a helper script that tunes the theme score threshold on the gold set, with a note that tuning and reporting on the same data inflates metrics. If feasible, split the gold set into tune and test halves and report on the test half only.

---

## 9. Impact analysis (`impact.py`)  — the part that makes this an analytics project

Use `statsmodels`. Use English reviews only. Compute and save:

1. **Theme prevalence:** share of reviews mentioning each theme, overall and by month.
2. **OLS regression:** `rating ~ theme flags (all themes simultaneously) + word_count + app_version (top-N versions, rest grouped) + month fixed effects`. Use heteroskedasticity-robust standard errors (HC3). Output each theme's coefficient, 95% CI, and p-value.
3. **Logistic regression** for `is_negative_rating` as a robustness check, and compare the direction and rank of effects with the OLS.
4. **What-if simulation:** for each theme, the estimated change in average rating if mentions of that theme were eliminated (coefficient x prevalence, with a bootstrap 95% CI, 1,000 resamples).
5. **Priority score:** `prevalence x estimated rating penalty`, ranked. Produce a ranked "fix list" table.
6. **Sensitivity checks:** multicollinearity (VIF), and a rerun with only single-theme reviews, to show the ranking is stable. Flag when it is not.
7. **Limitations text** (saved into `metrics.json` and shown in the dashboard): observational data, self-selection of reviewers, reviews are not a random sample of users, themes are noisy labels, and "impact" means statistical association.

---

## 10. Version and time analysis (`versions.py`)

- Theme share and average rating per app version (only versions with at least `min_reviews_per_version` reviews).
- Weekly time series of rating, volume, and share of each theme.
- **Spike detection:** flag weeks where a theme's share exceeds its trailing 8-week mean by more than 2 standard deviations, and list the app versions active in those weeks.
- **Pre/post comparison** around version releases that show a rating drop: report the change in average rating and the themes whose share increased most, with a simple significance test. Phrase these as leads for investigation.

---

## 11. Streamlit app (`app/`)

Multipage Streamlit app that reads only `data/processed/`. Use Plotly for charts, `st.cache_data` for loading, and a consistent, clean layout. Sidebar filters (date range, app version, rating, theme) applied across pages where it makes sense.

**Pages:**
1. **Overview:** KPI cards (average rating, review count, % negative, % English analyzed), rating trend, top themes bar chart, a data freshness stamp ("data through <date>").
2. **Theme trends:** weekly/monthly share per theme, multi-select, with spike markers.
3. **Fix priorities (the headline page):** the ranked fix list with prevalence, estimated rating penalty with CI, the what-if "rating if fixed" value, and a plain-language recommendation for each of the top 3 (generated from a template, not an LLM).
4. **Version explorer:** rating and theme share by app version, flagged regressions.
5. **Review explorer:** filterable table of example reviews per theme (text truncated, with a download button for the filtered rows).
6. **Methodology and quality:** data-quality report (pass/warn/fail badges), validation metrics from the gold set (or a "pending" notice), model details, limitations.

Requirements: loads in under 5 seconds on a cold cache, works on mobile width, handles missing files gracefully with a helpful message, and shows no reviewer names.

---

## 12. Orchestration and automation

**`run_pipeline.py`** with CLI flags: `--stage {ingest,clean,sentiment,themes,validate,impact,versions,export,all}`, `--sample N` (process only N reviews for quick tests), and `--full-refresh`.

**`.github/workflows/refresh.yml`:**
- Triggers: weekly schedule (cron) and `workflow_dispatch`.
- Steps: checkout, set up Python 3.11, cache pip and the Hugging Face model cache, install `requirements-pipeline.txt`, restore the DB, run the pipeline incrementally, run the data-quality gate, commit the updated `data/processed/` files only if checks pass and files changed (use a bot commit message with the date).
- Use `permissions: contents: write` minimal scope. No secrets are needed.
- Include a timeout and a note on the expected runtime.

**`.github/workflows/tests.yml`:** run `pytest` and `ruff` on every push and pull request.

---

## 13. Tests (`tests/`)

At minimum:
- Cleaning: dedupe, min-words filter, language filter on small fixtures.
- Quality checks: each check passes and fails correctly on synthetic data.
- Theme tagger: known sentences map to expected themes; multi-label and `Other` cases.
- Impact: on **synthetic data with a known planted effect**, the regression recovers the coefficient within tolerance.
- Idempotence: running ingest and clean twice does not change row counts.
- App: a smoke test that imports the app modules without torch installed.

---

## 14. README.md (recruiter-facing)

Write it so a recruiter understands the project in 60 seconds. Sections:
1. Title, one-line pitch, and a **live-demo link placeholder** at the very top
2. The business problem
3. Key findings (auto-filled from `metrics.json`; use real computed numbers only)
4. Dashboard screenshots (store in `docs/`)
5. Architecture diagram (Mermaid)
6. Methodology in plain language (ingestion, cleaning, sentiment, themes, validation, impact)
7. Validation results (or "pending: gold set not yet labeled")
8. Limitations and what I would do next (Hinglish support, causal methods, more apps, LLM-assisted theme naming)
9. How to run locally and how the automated refresh works
10. Tech stack
11. A resume-bullet suggestion block with placeholders for the real metrics

Write a small script `scripts/render_readme_findings.py` that fills the "Key findings" section from `metrics.json` so the README never contains made-up numbers.

---

## 15. Build order (milestones)

Stop after each milestone, run its tests, and summarize what was verified.

1. **Scaffold:** repo structure, config, requirements files, `.gitignore`, CI skeleton.
2. **Ingestion and storage:** verify the app ID, then pull a small sample (about 2,000 reviews) and confirm idempotence.
3. **Cleaning and data-quality checks** with tests.
4. **Sentiment** on the sample, with the agreement report.
5. **Themes:** write `themes.yaml`, build the tagger, run the discovery notebook, and generate `gold_template.csv`.
6. **Impact and version analysis** with the synthetic-data test.
7. **Export and Streamlit app** using the sample data; test locally in a clean environment that has only `requirements.txt` installed.
8. **Automation:** GitHub Actions workflows.
9. **README and docs.**
10. **Full run:** only after I approve, run the full backfill and regenerate all outputs.

---

## 16. Things you must ask me to do (do not attempt or fake them)

- Hand-label the gold set (`gold_labeled.csv`).
- Create the public GitHub repository, push the code, and enable Actions.
- Deploy on Streamlit Community Cloud and paste the live link into the README.
- Approve the implementation plan and approve the full-data run.

---

## 17. Definition of done

- `python src/run_pipeline.py --stage all` runs end to end on the sample and on the full data without errors.
- All tests pass and `ruff` is clean.
- The app runs locally with only `requirements.txt` installed, and shows no reviewer names.
- `data/processed/` contains every file the app needs, and the app handles missing or partial files gracefully.
- The refresh workflow is syntactically valid and its steps have been dry-run reviewed.
- The README contains no invented metrics, and the limitations are stated honestly.
- Final summary from you lists: what was built, what was verified and how, known limitations, and the manual steps remaining for me.
