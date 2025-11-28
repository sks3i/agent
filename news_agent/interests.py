"""Interest configuration loaders."""
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests

from .defaults import DEFAULT_FEEDS, DEFAULT_KEYWORDS


@dataclass
class Interest:
    name: str
    keywords: List[str]
    feeds: List[str]
    limit: Optional[int] = None


def _interest_from_dict(entry: dict, default_limit: int, fallback: Interest) -> Interest:
    return Interest(
        name=entry.get("name", fallback.name),
        keywords=entry.get("keywords") or fallback.keywords,
        feeds=entry.get("feeds") or fallback.feeds,
        limit=entry.get("limit", default_limit),
    )


def load_interests(default_limit: int, fallback_keywords: Optional[List[str]] = None, fallback_feeds: Optional[List[str]] = None) -> List[Interest]:
    keywords = fallback_keywords or DEFAULT_KEYWORDS
    feeds = fallback_feeds or DEFAULT_FEEDS
    default_interest = Interest(name="default", keywords=keywords, feeds=feeds, limit=default_limit)

    url = os.getenv("NEWS_AGENT_INTERESTS_URL")
    path = Path(os.getenv("NEWS_AGENT_INTERESTS_FILE", "news_agent/interests.json"))
    data = None
    if url:
        logging.debug("Fetching interests from %s", url)
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            logging.warning("Interest URL %s returned %s", url, response.status_code)
        else:
            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                logging.error("Interest URL %s returned invalid JSON: %s", url, exc)
    elif path.exists():
        logging.debug("Loading interests from %s", path)
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            logging.error("Unable to parse %s: %s", path, exc)

    if isinstance(data, list):
        interests: List[Interest] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            interests.append(_interest_from_dict(entry, default_limit, default_interest))
        if interests:
            return interests

    return [default_interest]
