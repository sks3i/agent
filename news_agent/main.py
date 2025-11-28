"""Entry point that ties collection, deduplication, summarization, and delivery."""
from argparse import ArgumentParser
from datetime import datetime
import os
from typing import List, Optional

from dotenv import load_dotenv

from .collector import NewsCollector
from .messenger import Messenger
from .storage import NewsHistory
from .summarizer import LLMSummarizer
from .interests import load_interests


def _split_env(env_key: str, fallback: Optional[List[str]] = None) -> List[str]:
    value = os.getenv(env_key)
    if not value:
        return fallback or []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    load_dotenv()
    parser = ArgumentParser(description="Run the personalized news digest pipeline.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum new stories to process")
    parser.add_argument("--dry-run", action="store_true", help="Do not send notifications or mark articles as seen")
    args = parser.parse_args()

    feeds = _split_env("NEWS_AGENT_FEEDS")
    keywords = _split_env("NEWS_AGENT_KEYWORDS", [])
    history_db = os.getenv("NEWS_AGENT_DB", "news_agent/story_history.db")
    ntfy_topic = os.getenv("NTFY_TOPIC")

    interests = load_interests(
        default_limit=args.limit,
        fallback_keywords=keywords or None,
        fallback_feeds=feeds or None,
    )
    collector = NewsCollector(default_limit=args.limit)
    articles = collector.collect(interests)

    print("Configured interest profiles:")
    for interest in interests:
        limit_marker = interest.limit or args.limit
        print(
            f"- {interest.name}: {len(interest.keywords)} keywords, {len(interest.feeds)} feeds, "
            f"limit {limit_marker}"
        )
    if articles:
        print("Collected articles:")
        for idx, article in enumerate(articles, start=1):
            tag = f"[{article.interest}]" if article.interest else ""
            print(f"{idx}. {tag} {article.title} ({article.url})")
    else:
        print("Collector found no articles before deduplication.")

    history = NewsHistory(db_path=history_db)
    try:
        seen_flags = list(history.has_seen(article.url for article in articles))
        new_articles = [article for article, seen in zip(articles, seen_flags) if not seen]

        if not new_articles:
            print("No new articles matched the filters today.")
            return

        summarizer = LLMSummarizer()
        gathered_keywords = sorted({kw for interest in interests for kw in interest.keywords})
        summary = summarizer.summarize(new_articles, keywords=gathered_keywords)

        article_lines = "\n".join(f"{idx + 1}. {article.title} ({article.url})" for idx, article in enumerate(new_articles))
        body = (
            f"{summary}\n\n" f"Detailed links:\n{article_lines}\n"
        )
        title = f"News digest · {len(new_articles)} articles · {datetime.utcnow().date()}"

        messenger = Messenger(ntfy_topic=ntfy_topic, dry_run=args.dry_run)
        messenger.send(title=title, body=body)

        if not args.dry_run:
            for article in new_articles:
                history.mark_seen(article.url, article.title)
        else:
            print("Dry run mode: stories not marked as seen.")
    finally:
        history.close()


if __name__ == "__main__":
    main()
