from __future__ import annotations
import logging
import time
from typing import Optional
import requests

log = logging.getLogger("notify")


class Notifier:
    """Slack/Telegram 간단 Webhook 알림. 실패 시 백오프 재시도."""

    def __init__(
        self,
        slack_webhook: Optional[str] = None,
        telegram_bot: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        self.slack_webhook = slack_webhook
        self.telegram_bot = telegram_bot
        self.telegram_chat_id = telegram_chat_id

    def send(self, text: str) -> None:
        ok = False
        # Slack
        if self.slack_webhook:
            ok |= self._post_slack(text)
        # Telegram
        if self.telegram_bot and self.telegram_chat_id:
            ok |= self._post_telegram(text)
        if not ok:
            log.debug("No notifier configured; message dropped: %s", text)

    def _post_slack(self, text: str) -> bool:
        payload = {"text": text}
        if not self.slack_webhook:
            return False
        return self._retry_post(
            str(self.slack_webhook), json=payload
        )  # ✅ str() 캐스팅 추가

    def _post_telegram(self, text: str) -> bool:
        if not (self.telegram_bot and self.telegram_chat_id):
            return False
        url = f"https://api.telegram.org/bot{self.telegram_bot}/sendMessage"
        payload = {"chat_id": self.telegram_chat_id, "text": text}
        return self._retry_post(str(url), data=payload)  # ✅ str() 캐스팅 추가

    def _retry_post(self, url: str, **kwargs) -> bool:
        backoff = 0.5
        for _ in range(4):
            try:
                r = requests.post(url, timeout=5, **kwargs)
                if r.status_code >= 400:
                    raise requests.HTTPError(f"status={r.status_code}", response=r)
                return True
            except Exception as e:
                log.warning("notify post failed: %s (retry %.1fs)", e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 6.0)
        return False
