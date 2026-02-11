"""
Unit tests for BranchRouter.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from processors.branch_router import BranchRouter, PRIORITY_LEVELS


class TestBranchRouterDefaults(unittest.TestCase):
    """Test default routing rules."""

    def setUp(self):
        self.router = BranchRouter()

    def test_document_routes_to_summarize(self):
        op, priority = self.router.route({'type': 'document', 'priority': 'normal'})
        self.assertEqual(op, 'summarize')

    def test_image_routes_to_file_copy(self):
        op, priority = self.router.route({'type': 'image', 'priority': 'normal'})
        self.assertEqual(op, 'file_copy')

    def test_data_routes_to_summarize(self):
        op, priority = self.router.route({'type': 'data'})
        self.assertEqual(op, 'summarize')

    def test_email_routes_to_summarize(self):
        op, priority = self.router.route({'type': 'email'})
        self.assertEqual(op, 'summarize')

    def test_unknown_type_defaults_to_summarize(self):
        op, priority = self.router.route({'type': 'video'})
        self.assertEqual(op, 'summarize')

    def test_missing_type_defaults_to_summarize(self):
        op, priority = self.router.route({})
        self.assertEqual(op, 'summarize')


class TestBranchRouterCustomRules(unittest.TestCase):
    """Test custom routing rules."""

    def test_custom_rules_override_defaults(self):
        router = BranchRouter(custom_rules={'document': 'file_copy'})
        op, _ = router.route({'type': 'document'})
        self.assertEqual(op, 'file_copy')

    def test_custom_rules_add_new_types(self):
        router = BranchRouter(custom_rules={'video': 'file_create'})
        op, _ = router.route({'type': 'video'})
        self.assertEqual(op, 'file_create')

    def test_default_rules_preserved_with_custom(self):
        router = BranchRouter(custom_rules={'video': 'file_create'})
        op, _ = router.route({'type': 'image'})
        self.assertEqual(op, 'file_copy')


class TestBranchRouterPriority(unittest.TestCase):
    """Test priority handling."""

    def setUp(self):
        self.router = BranchRouter()

    def test_priority_returned(self):
        _, priority = self.router.route({'type': 'document', 'priority': 'critical'})
        self.assertEqual(priority, 'critical')

    def test_invalid_priority_defaults_to_normal(self):
        _, priority = self.router.route({'type': 'document', 'priority': 'invalid'})
        self.assertEqual(priority, 'normal')

    def test_priority_values(self):
        self.assertEqual(self.router.get_priority_value('critical'), 4)
        self.assertEqual(self.router.get_priority_value('high'), 3)
        self.assertEqual(self.router.get_priority_value('normal'), 2)
        self.assertEqual(self.router.get_priority_value('low'), 1)
        self.assertEqual(self.router.get_priority_value('invalid'), 2)


if __name__ == '__main__':
    unittest.main()
