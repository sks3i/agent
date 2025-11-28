"""Push-based delivery helpers (ntfy as primary channel)."""
from typing import Optional
import requests


class Messenger:
    def __init__(self, ntfy_topic: Optional[str] = None, dry_run: bool = False):
        self.ntfy_topic = ntfy_topic
        self.dry_run = dry_run

    def send(self, title: str, body: str, priority: int = 3) -> None:
        if self.dry_run:
            print("[dry-run] Notification suppressed")
            print(f"Title: {title}")
            print(body)
            return

        if not self.ntfy_topic:
            raise RuntimeError("No notification target configured (set NTFY_TOPIC)")

        headers = {
            "Title": title,
            "Priority": str(priority),
            "Tags": "news,daily",
        }
        response = requests.post(
            f"https://ntfy.sh/{self.ntfy_topic}", data=body.encode("utf-8"), headers=headers, timeout=15
        )
        response.raise_for_status()
