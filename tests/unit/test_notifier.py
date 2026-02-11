"""Unit tests for Notifier and WebhookNotifier."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from notifications.notifier import NoOpNotifier
from notifications.webhook_notifier import WebhookNotifier


class TestNoOpNotifier(unittest.TestCase):
    """Test NoOpNotifier (graceful no-op)."""

    def test_send_returns_true(self):
        notifier = NoOpNotifier()
        result = notifier.send({'task_name': 'test', 'new_status': 'done'})
        self.assertTrue(result)

    def test_send_empty_event_returns_true(self):
        notifier = NoOpNotifier()
        result = notifier.send({})
        self.assertTrue(result)


class TestWebhookNotifier(unittest.TestCase):
    """Test WebhookNotifier."""

    @patch('notifications.webhook_notifier.urlopen')
    def test_successful_send(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock()
        notifier = WebhookNotifier('http://localhost:8080/webhook')
        result = notifier.send({
            'task_name': 'test.md',
            'old_status': 'pending',
            'new_status': 'done',
        })
        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    @patch('notifications.webhook_notifier.urlopen')
    def test_failure_returns_false_no_raise(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError('Connection refused')
        notifier = WebhookNotifier('http://localhost:8080/webhook')
        result = notifier.send({'task_name': 'test.md', 'new_status': 'done'})
        self.assertFalse(result)

    @patch('notifications.webhook_notifier.urlopen')
    def test_failure_logs_notification_failed(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError('Connection refused')
        mock_logger = MagicMock()
        notifier = WebhookNotifier(
            'http://localhost:8080/webhook', ops_logger=mock_logger
        )
        notifier.send({'task_name': 'test.md', 'new_status': 'done'})
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        self.assertEqual(call_args.kwargs.get('op') or call_args[1].get('op', ''), 'notification_failed')


if __name__ == '__main__':
    unittest.main()
