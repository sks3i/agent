# Personal Tech Briefing Agent

This repository hosts a lightweight pipeline that fetches, deduplicates, and summarizes new technical articles or research updates for a daily (or scheduled) teaching-friendly briefing. Think of it as a five-minute deep-dive delivered where you already pay attention—your phone, email, or chat app—without opening yet another news app.

## Pipeline Overview

1. **Trigger (Scheduler)**
   - Use cron, GitHub Actions, or any scheduler to call `python -m news_agent.main` at the hour you prefer your teaching refresher.
2. **Collector**
   - RSS feeds are polled for matching keywords that align with the daily teaching topic. When the feeds are empty, the pipeline falls back to an ArXiv API query so your teaching slot still receives something fresh.
3. **Processor**
   - The pipeline scrapes fresh articles, deduplicates them with SQLite history, and feeds them to an LLM to craft a concise “what-you-need-to-know” summary.
4. **Messenger**
   - The briefing is sent via push services such as `ntfy.sh` or `pushover`, or printed when running in dry-run mode for offline review.

## Configuration

Copy `.env.example` into `.env` (if desired) then export the following environment variables prior to running:

- `NEWS_AGENT_FEEDS` (optional) – comma-separated RSS feed URLs (uses a sane default if unset).
- `NEWS_AGENT_KEYWORDS` – comma-separated keywords that describe the niche you care about.
- `NEWS_AGENT_INTERESTS_URL` – optional URL (GitHub Gist raw, object storage, etc.) that lists the interest buckets plus per-interest limits so you can tweak interests without pushing new commits.
- `NEWS_AGENT_INTERESTS_FILE` – optional path to a JSON file (defaults to `news_agent/interests.json`, ignored by git) for local overrides.
- `NEWS_AGENT_DB` – path to the SQLite file; defaults to `news_agent/story_history.db`.
- `OPENAI_API_KEY` – optional; when present, the script will call OpenAI's chat completion API to produce higher-quality summaries.
- `LLM_ENDPOINT` – optional HTTP endpoint for alternative LLM providers (takes precedence over OpenAI if set).
- `NTFY_TOPIC` or `PUSHOVER_TOKEN`/`PUSHOVER_USER` – configure the messenger service.

## Running locally

```bash
python -m news_agent.main
```

Optionally add `--dry-run` to skip sending notifications or `--limit 5` to cap how many new articles are processed.

## Scheduling examples

- Cron (runs at your preferred teaching slot, e.g., 8 AM):
  ```cron
  0 8 * * * cd /path/to/agent && . /path/to/.env && python -m news_agent.main
  ```
- GitHub Actions: see `.github/workflows/daily-news.yml`.

## Interest configuration

- Create `news_agent/interests.json` (copy from `news_agent/interests.sample.json`) and edit the bucket list locally; the file is git-ignored so you can tweak interests without committing.
- Prefer editing remotely? host the same JSON somewhere (e.g., GitHub Gist raw URL) and point `NEWS_AGENT_INTERESTS_URL` at it — the workflow will pull the latest interests every run.
- Each bucket can specify its own `limit`, so the collector tries to grab that many articles per focus area before deduplication (the CLI `--limit` still acts as the default per-interest limit if none is provided).

## Testing

```bash
python -m news_agent.main --dry-run --limit 2
```

The script writes/reads from the configured SQLite database and reports which articles it will summarize/send.
