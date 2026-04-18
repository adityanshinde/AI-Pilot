# Autopilot Content Engine

Production-oriented CrewAI system that collects user pain points from social channels, clusters them with NLP, generates multi-platform content, and publishes automatically.

## Architecture

- `connectors/`: external integrations (Reddit, Threads, Blogger)
- `db/`: SQLAlchemy schema, session, repository, init
- `agents/`: CrewAI role modules with typed schemas
- `utils/`: settings, logging, retries, NLP, embeddings, LLM helper
- `pipelines/`: end-to-end orchestration
- `prompts/`: agent prompts editable without code changes
- `.github/workflows/`: scheduler every 6 hours

## Setup

1. Create Python 3.10+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy env template and set values:
   ```bash
   cp .env.example .env
   ```
4. Ensure PostgreSQL is reachable via `DATABASE_URL`.

## Run Locally

Initialize DB:
```bash
python main.py init_db
```

Run full pipeline once:
```bash
python main.py run_once
```

Optional (skip create-all in runtime):
```bash
python main.py run_once --no-init-db
```

## Idempotency

- `raw_posts`: unique on `(source_platform, source_post_id, source_type)`
- `processed_problems`: unique on `raw_post_id`
- `content_generated`: unique on `(cluster_hash, content_type)` and `content_hash`
- `published_logs`: unique on `(content_generated_id, platform, status)`

This prevents duplicate content generation and duplicate publishing across scheduled runs.

## Required Secrets (GitHub Actions)

- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`
- PostgreSQL: `DATABASE_URL`
- Reddit: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_SUBREDDITS`, `REDDIT_FETCH_LIMIT`, `REDDIT_TARGET_SUBREDDIT`
- Threads: `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID`, `THREADS_SEARCH_TERMS`, `THREADS_SCRAPE_RSS_URL` (optional fallback)
- Blogger: `BLOGGER_BLOG_ID`, `BLOGGER_ACCESS_TOKEN` or `BLOGGER_API_KEY`

## Notes

- Set `DRY_RUN=true` while validating end-to-end flow.
- For production publishing, set `DRY_RUN=false`.
- Strategy/content generation use CrewAI with model selected by `OPENAI_MODEL`.
