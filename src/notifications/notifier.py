"""
Abstract Notifier for Gold Tier Foundation + Platinum Intelligence Layer.

Base class for all notification delivery mechanisms.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

# Alert types (Gold + Platinum)
ALERT_TYPES = {
    # Gold
    'status_change', 'execution_failure', 'sla_breach',
    'credential_detected', 'rollback_triggered',
    # Platinum
    'predictive_sla_warning', 'self_healing_recovery',
    'concurrency_limit_reached',
}


class Notifier(ABC):
    """
    Abstract base class for notification delivery.

    Implementations must be fire-and-forget: never raise exceptions
    that could block task processing.
    """

    @abstractmethod
    def send(self, event: dict) -> bool:
        """
        Send a notification event.

        Args:
            event: Dict with keys: task_name, old_status, new_status,
                   timestamp, severity. Platinum adds: alert_type
                   (predictive_sla_warning, self_healing_recovery,
                   concurrency_limit_reached).

        Returns:
            True if sent successfully, False otherwise.
        """
        pass


class NoOpNotifier(Notifier):
    """
    No-op notifier for when notifications are not configured.

    Returns True without doing anything.
    """

    def send(self, event: dict) -> bool:
        """No-op send — returns True silently."""
        return True
