"""
Branch Router for Gold Tier Conditional Workflows.

Routes tasks to operations based on type, priority, and source attributes.
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

PRIORITY_LEVELS = {
    'critical': 4,
    'high': 3,
    'normal': 2,
    'low': 1,
}


class BranchRouter:
    """
    Routes tasks to operations based on type, priority, and source.

    Default routing rules:
        document → summarize
        image → file_copy
        data → summarize
        email → summarize
    """

    DEFAULT_ROUTING_RULES = {
        'document': 'summarize',
        'image': 'file_copy',
        'data': 'summarize',
        'email': 'summarize',
    }

    def __init__(self, custom_rules: Optional[Dict[str, str]] = None):
        """
        Initialize BranchRouter.

        Args:
            custom_rules: Optional dict overriding default type→operation mapping.
        """
        self.routing_rules = self.DEFAULT_ROUTING_RULES.copy()
        if custom_rules:
            self.routing_rules.update(custom_rules)

    def route(self, task_metadata: dict) -> Tuple[str, str]:
        """
        Route a task to an operation based on metadata.

        Args:
            task_metadata: Dict with keys: type, priority, source.

        Returns:
            Tuple of (operation_name, priority_level).
        """
        task_type = task_metadata.get('type', 'unknown')
        priority = task_metadata.get('priority', 'normal')
        source = task_metadata.get('source', 'unknown')

        if priority not in PRIORITY_LEVELS:
            logger.warning(f"Invalid priority '{priority}', defaulting to 'normal'")
            priority = 'normal'

        if task_type in self.routing_rules:
            operation = self.routing_rules[task_type]
            logger.info(
                f"Branch decision: type={task_type} priority={priority} "
                f"source={source} -> operation={operation}"
            )
        else:
            operation = 'summarize'
            logger.warning(
                f"Unknown task type '{task_type}', defaulting to 'summarize'"
            )

        return operation, priority

    def get_priority_value(self, priority: str) -> int:
        """Get numeric priority value for sorting (higher = more urgent)."""
        return PRIORITY_LEVELS.get(priority, PRIORITY_LEVELS['normal'])
