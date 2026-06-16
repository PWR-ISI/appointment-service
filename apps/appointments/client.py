"""HTTP client that appointment-service uses to talk to schedule-service."""
import logging
from typing import Optional

import requests
import urllib3.util.retry as retry_module
from django.conf import settings
from requests.adapters import HTTPAdapter

from common.exceptions import ScheduleServiceError, SlotUnavailable

logger = logging.getLogger(__name__)


class ScheduleClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        self.base = (base_url or settings.SCHEDULE_SERVICE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        retries = retry_module.Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _headers(self) -> dict:
        return {
            "X-Internal-Token": settings.INTERNAL_SHARED_TOKEN,
            "Content-Type": "application/json",
        }

    def reserve_slot(self, slot_id, appointment_id, ttl_minutes: Optional[int] = None) -> dict:
        url = f"{self.base}/api/v1/slots/{slot_id}/reserve"
        body = {"appointment_id": str(appointment_id)}
        if ttl_minutes is not None:
            body["ttl_minutes"] = ttl_minutes
        try:
            r = self.session.post(url, json=body, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise ScheduleServiceError(f"Schedule service unreachable: {exc}") from exc
        if r.status_code == 409:
            raise SlotUnavailable(f"Slot {slot_id} not available.")
        if r.status_code >= 500:
            raise ScheduleServiceError(f"Schedule service error: HTTP {r.status_code}")
        r.raise_for_status()
        return r.json()

    def release_slot(self, slot_id) -> None:
        url = f"{self.base}/api/v1/slots/{slot_id}/release"
        try:
            r = self.session.post(url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            logger.warning("Schedule release failed: %s", exc)
            return
        if r.status_code >= 500:
            logger.warning("Schedule release returned %s", r.status_code)

    def confirm_slot(self, slot_id) -> None:
        url = f"{self.base}/api/v1/slots/{slot_id}/confirm"
        try:
            r = self.session.post(url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            logger.warning("Schedule confirm failed: %s", exc)
            return
        if r.status_code >= 500:
            logger.warning("Schedule confirm returned %s", r.status_code)
