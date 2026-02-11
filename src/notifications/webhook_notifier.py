"""
Webhook Notifier for Gold Tier Foundation.

Sends fire-and-forget HTTP POST notifications to a configured endpoint.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from notifications.notifier import Notifier
from utils.operations_logger import OperationsLogger

logger = logging.getLogger(__name__)


class WebhookNotifier(Notifier):
    """
    Sends notifications via HTTP POST to a webhook endpoint.

    Fire-and-forget: wraps POST in try/except, logs outcome,
    never raises exceptions that could block processing.
    """

    def __init__(self, endpoint: str,
                 ops_logger: Optional[OperationsLogger] = None,
                 timeout: int = 5):
        """
        Initialize WebhookNotifier.

        Args:
            endpoint: URL to POST notifications to.
            ops_logger: Optional OperationsLogger for audit trail.
            timeout: HTTP request timeout in seconds.
        """
        self.endpoint = endpoint
        self.ops_logger = ops_logger
        self.timeout = timeout

    def send(self, event: dict) -> bool:
        """
        Send a notification event via HTTP POST.

        Payload: JSON with task_name, old_status, new_status,
        timestamp, severity.

        Args:
            event: Notification event dict.

        Returns:
            True if sent successfully, False otherwise.
        """
        payload = {
            'task_name': event.get('task_name', 'unknown'),
            'old_status': event.get('old_status', ''),
            'new_status': event.get('new_status', ''),
            'timestamp': event.get('timestamp', datetime.now().isoformat()),
            'severity': event.get('severity', 'info'),
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = Request(
                self.endpoint,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            urlopen(req, timeout=self.timeout)

            logger.info(f"Notification sent: {payload['task_name']} → {payload['new_status']}")

            if self.ops_logger:
                self.ops_logger.log(
                    op='notification_sent',
                    file=payload['task_name'],
                    src='webhook',
                    dst=self.endpoint,
                    outcome='success',
                    detail=f"status:{payload['old_status']}→{payload['new_status']}"
                )

            return True

        except URLError as e:
            logger.warning(f"Notification failed (URL error): {e}")
            self._log_failure(payload, str(e))
            return False
        except Exception as e:
            logger.warning(f"Notification failed: {e}")
            self._log_failure(payload, str(e))
            return False

    def _log_failure(self, payload: dict, error: str) -> None:
        """Log notification failure."""
        if self.ops_logger:
            self.ops_logger.log(
                op='notification_failed',
                file=payload.get('task_name', 'unknown'),
                src='webhook',
                dst=self.endpoint,
                outcome='failed',
                detail=f"error:{error}"
            )
