"""LLM-backed summarizer with a fallback summarization path."""
import os
from typing import Iterable, List, Optional
from textwrap import shorten
import logging

import requests

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None  # type: ignore[arg-type]

from .collector import Article


class LLMSummarizer:
    def __init__(self, model: str = "gpt-4.1-mini", max_tokens: int = 600):
        self.model = model
        self.max_tokens = max_tokens
        self.llm_endpoint = os.getenv("LLM_ENDPOINT")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai and self.openai_api_key:
            openai.api_key = self.openai_api_key

    def summarize(self, articles: Iterable[Article], keywords: Optional[List[str]] = None) -> str:
        articles = list(articles)
        if not articles:
            return "No fresh stories matched your filters today."

        context = "\n\n".join(
            f"{article.title}\n{article.url}\n{shorten(article.summary or '', 200)}"
            for article in articles
        )
        system_prompt = (
            "You are a concise research assistant that digests technical writing. "
            "Focus on novel details, experimental setups, and limitations relevant to the user-supplied keywords."
        )
        keyword_context = f"pertain to {', '.join(keywords)}" if keywords else "match the stated interests"
        user_prompt = (
            f"Analyze the following articles and summarize the core insights that {keyword_context}. "
            "Highlight the technical innovations, experiments, and why the work matters for this niche."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_prompt}\n\n{context}"},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
        }

        if self.llm_endpoint:
            logging.debug("Calling custom LLM endpoint %s", self.llm_endpoint)
            response = requests.post(self.llm_endpoint, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"].strip()
            return data.get("summary", "")

        if openai and self.openai_api_key:
            logging.debug("Calling OpenAI model %s", self.model)
            chat = openai.chat.completions.create(**payload)
            return chat.choices[0].message.content.strip()

        logging.warning("LLM API not configured; falling back to lightweight summary.")
        lines = []
        for article in articles:
            lines.append(f"• {article.title}: {shorten(article.summary or 'No summary available.', 140)}")
        return "\n".join(lines)
