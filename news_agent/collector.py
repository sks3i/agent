"""Feed-based collector that gathers articles matching a keyword set."""
from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import quote_plus

import feedparser
import logging

from .defaults import DEFAULT_FEEDS, DEFAULT_KEYWORDS
from .interests import Interest

ARXIV_API_BASE = "https://export.arxiv.org/api/query"


@dataclass
class Article:
    title: str
    url: str
    published: Optional[str]
    summary: str
    interest: Optional[str] = None


class NewsCollector:
    def __init__(self, default_limit: int = 5):
        self.default_limit = default_limit

    def collect(self, interests: Iterable["Interest"]) -> List[Article]:
        interest_list = list(interests)
        articles: List[Article] = []
        for interest in interest_list:
            buffer = self._collect_for_interest(interest)
            articles.extend(buffer[: interest.limit or self.default_limit])
        if not articles:
            logging.info("No articles from RSS feeds; falling back to ArXiv API search.")
            fallback_keywords = list({keyword for interest in interest_list for keyword in interest.keywords})
            fallback = self._fetch_arxiv_api(fallback_keywords)
            fallback_limit = next((interest.limit for interest in interest_list if interest.limit), self.default_limit)
            articles.extend(fallback[: fallback_limit])
        return articles

    def _collect_for_interest(self, interest: "Interest") -> List[Article]:
        matched: List[Article] = []
        feeds = interest.feeds or DEFAULT_FEEDS
        limit = interest.limit or self.default_limit
        for feed_url in feeds:
            parsed = feedparser.parse(feed_url)
            entries = getattr(parsed, "entries", [])
            logging.debug("Feed %s yielded %d entries", feed_url, len(entries))
            for entry in entries:
                if len(matched) >= limit:
                    break
                url = entry.get("link")
                title = entry.get("title", "Untitled")
                summary = entry.get("summary", "")
                published = entry.get("published")
                if not url:
                    continue
                if self._matches_keywords(interest.keywords, title + summary):
                    matched.append(
                        Article(
                            title=title.strip(),
                            url=url,
                            published=published,
                            summary=summary.strip(),
                            interest=interest.name,
                        )
                    )
            if len(matched) >= limit:
                break
        return matched

    def _matches_keywords(self, keywords: List[str], text: str) -> bool:
        if not keywords:
            return True
        lowered = text.lower()
        return any(keyword.lower() in lowered for keyword in keywords)

    def _fetch_arxiv_api(self, keywords: Iterable[str]) -> List[Article]:
        keyword_list = [keyword for keyword in keywords if keyword.strip()]
        if not keyword_list:
            keyword_list = DEFAULT_KEYWORDS
        query = "+OR+".join(f"all:{quote_plus(keyword)}" for keyword in keyword_list)
        url = f"{ARXIV_API_BASE}?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={self.default_limit}"
        parsed = feedparser.parse(url)
        entries = getattr(parsed, "entries", [])
        logging.info("ArXiv API returned %d entries for query %s", len(entries), query)
        results: List[Article] = []
        for entry in entries:
            url = entry.get("link")
            if not url:
                continue
            published = entry.get("published")
            summary = entry.get("summary", "")
            title = entry.get("title", "Untitled")
            results.append(
                Article(
                    title=title.strip(),
                    url=url,
                    published=published,
                    summary=summary.strip(),
                    interest="fallback",
                )
            )
        return results
