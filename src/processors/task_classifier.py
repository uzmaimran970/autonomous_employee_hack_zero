"""
Task Classifier for Gold Tier Foundation.

Implements six-gate classification to determine if a task
is simple (auto-executable), complex (multi-step), or manual_review.

Gates 1-3: Silver Tier (step count, credentials, determinism)
Gates 4-6: Gold Tier (permissions, SLA feasibility, rollback readiness)
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from utils.config import get_config

logger = logging.getLogger(__name__)

# Keywords that suggest credential/secret involvement
CREDENTIAL_KEYWORDS = [
    'password', 'secret', 'token', 'api_key', 'api-key',
    'credential', 'auth', 'oauth', 'private_key', 'access_key',
    'ssh', 'certificate', '.pem', '.key', '.env',
]

# Keywords that suggest non-deterministic operations
NON_DETERMINISTIC_KEYWORDS = [
    'api call', 'http request', 'download', 'upload',
    'send email', 'network', 'external service',
    'database', 'deploy', 'install',
]

# Keywords that suggest network/external service usage
NETWORK_KEYWORDS = [
    'http', 'https', 'api', 'curl', 'wget', 'fetch',
    'request', 'endpoint', 'webhook', 'socket',
]


class TaskClassifier:
    """
    Classifies tasks using a six-gate check.

    Gate 1: Step count — <= MAX_SIMPLE_STEPS = simple, <= MAX_COMPLEX_STEPS = complex, > = manual_review
    Gate 2: Credential check — no credential references
    Gate 3: Determinism — file-system-only, deterministic operations
    Gate 4: Permission check — operations within allowlist and vault scope
    Gate 5: SLA feasibility — estimated duration within threshold
    Gate 6: Rollback readiness — snapshot exists for complex tasks
    """

    SIMPLE_OPERATIONS = {
        'file_create', 'file_copy', 'summarize',
        'create file', 'copy file', 'create summary',
        'rename file', 'move file', 'create folder',
    }

    MAX_SIMPLE_STEPS = 5
    MAX_COMPLEX_STEPS = 15

    def __init__(self, vault_path: Optional[Path] = None, ops_logger=None):
        """
        Initialize TaskClassifier.

        Args:
            vault_path: Path to the vault root (for permission scope checks).
            ops_logger: Optional OperationsLogger for gate_blocked logging.
        """
        self.vault_path = Path(vault_path) if vault_path else None
        self.ops_logger = ops_logger

    def classify(self, task_content: str, plan_steps: List[str],
                 task_metadata: Optional[dict] = None) -> str:
        """
        Classify a task as simple, complex, or manual_review.

        Runs all 6 gates sequentially. Gate results are stored for
        frontmatter writing by the caller.

        Args:
            task_content: The full task file content.
            plan_steps: List of plan step strings.
            task_metadata: Optional task frontmatter dict for override check.

        Returns:
            'simple', 'complex', or 'manual_review'.
        """
        # Check for manual override
        if task_metadata and task_metadata.get('override'):
            logger.info("Classification: override detected — bypassing gates")
            self._gate_results = {
                'gate_1_step_count': 'skipped',
                'gate_2_credentials': 'skipped',
                'gate_3_determinism': 'skipped',
                'gate_4_permissions': 'skipped',
                'gate_5_sla': 'skipped',
                'gate_6_rollback': 'skipped',
                'override': True,
                'override_reason': task_metadata.get('override_reason', 'none'),
            }
            # Override still respects step count for classification tier
            actionable = self._count_actionable_steps(plan_steps)
            if actionable <= self.MAX_SIMPLE_STEPS:
                return 'simple'
            return 'complex'

        self._gate_results = {}

        # Gate 1: Step count
        actionable = self._count_actionable_steps(plan_steps)
        if actionable > self.MAX_COMPLEX_STEPS:
            self._gate_results['gate_1_step_count'] = 'fail:manual_review'
            logger.info(f"Classification: manual_review ({actionable} steps > {self.MAX_COMPLEX_STEPS})")
            self._fill_remaining_gates(2)
            return 'manual_review'

        is_simple_step_count = actionable <= self.MAX_SIMPLE_STEPS
        self._gate_results['gate_1_step_count'] = 'pass'

        # Gate 2: Credentials
        if not self._check_credentials(task_content, plan_steps):
            self._gate_results['gate_2_credentials'] = 'fail'
            logger.info("Classification: complex (credential reference)")
            self._fill_remaining_gates(3)
            return 'complex'
        self._gate_results['gate_2_credentials'] = 'pass'

        # Gate 3: Determinism
        if not self._check_determinism(plan_steps):
            self._gate_results['gate_3_determinism'] = 'fail'
            logger.info("Classification: complex (non-deterministic)")
            self._fill_remaining_gates(4)
            return 'complex'
        self._gate_results['gate_3_determinism'] = 'pass'

        # Gate 4: Permissions
        if not self._check_permissions(task_content, plan_steps):
            self._gate_results['gate_4_permissions'] = 'fail'
            logger.info("Classification: complex (permission denied)")
            self._fill_remaining_gates(5)
            return 'complex'
        self._gate_results['gate_4_permissions'] = 'pass'

        # Gate 5: SLA feasibility
        config = get_config()
        complexity_for_sla = 'simple' if is_simple_step_count else 'complex'
        if not self._check_sla_feasibility(complexity_for_sla, config):
            self._gate_results['gate_5_sla'] = 'fail'
            logger.info("Classification: complex (SLA infeasible)")
            self._fill_remaining_gates(6)
            return 'complex'
        self._gate_results['gate_5_sla'] = 'pass'

        # Gate 6: Rollback readiness (only relevant for complex tasks)
        if not is_simple_step_count:
            if not self._check_rollback_readiness(task_metadata):
                self._gate_results['gate_6_rollback'] = 'fail'
                logger.info("Classification: complex (rollback not ready)")
                return 'complex'
        self._gate_results['gate_6_rollback'] = 'pass' if not is_simple_step_count else 'skipped:simple'

        if is_simple_step_count:
            logger.info("Classification: simple (all 6 gates passed)")
            return 'simple'
        else:
            logger.info("Classification: complex (all 6 gates passed, multi-step)")
            return 'complex'

    def get_gate_results(self) -> Dict[str, str]:
        """Return the gate results from the last classify() call."""
        return getattr(self, '_gate_results', {})

    def _count_actionable_steps(self, plan_steps: List[str]) -> int:
        """Count non-empty, non-header steps."""
        return len([
            s for s in plan_steps
            if s.strip() and not s.strip().startswith('#')
        ])

    def _fill_remaining_gates(self, from_gate: int) -> None:
        """Fill remaining gate results as 'skipped' after a failure."""
        gate_names = {
            2: 'gate_2_credentials', 3: 'gate_3_determinism',
            4: 'gate_4_permissions', 5: 'gate_5_sla', 6: 'gate_6_rollback',
        }
        for g in range(from_gate, 7):
            if g in gate_names:
                self._gate_results[gate_names[g]] = 'skipped'

    def _check_step_count(self, plan_steps: List[str]) -> bool:
        """
        Gate 1: Check if task has few enough steps to be auto-executable.

        Returns:
            True if step count is within simple threshold, False if too many.
        """
        return self._count_actionable_steps(plan_steps) <= self.MAX_SIMPLE_STEPS

    def _check_credentials(self, task_content: str,
                           plan_steps: List[str]) -> bool:
        """
        Gate 2: Check for credential/secret references.

        Returns:
            True if no credentials found (passes gate), False otherwise.
        """
        combined = task_content.lower() + ' '.join(
            s.lower() for s in plan_steps)

        for keyword in CREDENTIAL_KEYWORDS:
            if keyword in combined:
                return False
        return True

    def _check_determinism(self, plan_steps: List[str]) -> bool:
        """
        Gate 3: Check if operations are deterministic and file-system-only.

        Returns:
            True if deterministic (passes gate), False otherwise.
        """
        combined = ' '.join(s.lower() for s in plan_steps)

        for keyword in NON_DETERMINISTIC_KEYWORDS:
            if keyword in combined:
                return False

        return True

    def _check_permissions(self, task_content: str,
                           plan_steps: List[str]) -> bool:
        """
        Gate 4: Check operations against ALLOWED_EXTERNAL_SERVICES allowlist
        and vault-only scope.

        Returns:
            True if all operations are permitted, False otherwise.
        """
        config = get_config()
        allowed_services = config.get('allowed_external_services', [])
        combined = task_content.lower() + ' '.join(s.lower() for s in plan_steps)

        # Check for network/external service references
        has_network_ref = any(kw in combined for kw in NETWORK_KEYWORDS)
        if has_network_ref and not allowed_services:
            self._log_gate_blocked('permission_gate', 'network_not_allowed')
            return False

        # Check if referenced services are in the allowlist
        if has_network_ref and allowed_services:
            # If network references exist, at least one allowed service must match
            service_found = any(
                svc.lower() in combined for svc in allowed_services
            )
            if not service_found:
                self._log_gate_blocked('permission_gate', 'service_not_in_allowlist')
                return False

        # Check vault-scope: block paths outside vault directory
        if self.vault_path:
            vault_str = str(self.vault_path).lower()
            # Look for absolute path references that aren't in the vault
            path_patterns = re.findall(r'(?:/[\w./]+)', combined)
            for path_ref in path_patterns:
                # Skip common non-path patterns
                if path_ref in ('/needs_action/', '/in_progress/', '/done/',
                                '/plans/', '/rollback_archive/'):
                    continue
                if len(path_ref) > 5 and vault_str not in path_ref:
                    # Potentially outside vault
                    self._log_gate_blocked('permission_gate', f'outside_vault:{path_ref}')
                    return False

        return True

    def _check_sla_feasibility(self, complexity: str,
                               config: Optional[dict] = None) -> bool:
        """
        Gate 5: Estimate duration from historical averages and flag if > 150% SLA.

        Args:
            complexity: 'simple' or 'complex'
            config: Config dict with SLA thresholds.

        Returns:
            True if estimated duration is feasible, False otherwise.
        """
        if config is None:
            config = get_config()

        sla_minutes = (config.get('sla_simple_minutes', 2)
                       if complexity == 'simple'
                       else config.get('sla_complex_minutes', 10))

        # Estimate from ops_logger historical data if available
        estimated_minutes = self._estimate_duration(complexity)
        if estimated_minutes is None:
            # No historical data — assume feasible
            return True

        threshold = sla_minutes * 1.5
        if estimated_minutes > threshold:
            self._log_gate_blocked(
                'sla_feasibility',
                f'estimated:{estimated_minutes:.1f}min > threshold:{threshold:.1f}min'
            )
            return False

        return True

    def _estimate_duration(self, complexity: str) -> Optional[float]:
        """
        Estimate task duration from historical operations log averages.

        Returns:
            Estimated minutes, or None if no historical data.
        """
        if not self.ops_logger:
            return None

        try:
            recent = self.ops_logger.read_recent(200)
            durations = []
            for entry in recent:
                if (entry.get('op') == 'task_executed' and
                        entry.get('outcome') == 'success'):
                    detail = entry.get('detail', '')
                    if f'complexity:{complexity}' in detail:
                        # Use a default average if no explicit duration
                        durations.append(1.0 if complexity == 'simple' else 5.0)

            if durations:
                return sum(durations) / len(durations)
        except Exception as e:
            logger.warning(f"Error estimating duration: {e}")

        return None

    def _check_rollback_readiness(self, task_metadata: Optional[dict] = None) -> bool:
        """
        Gate 6: Verify rollback snapshot exists for complex tasks before execution.

        For pre-execution classification, this checks if the rollback system
        is available. The actual snapshot is created before execution.

        Args:
            task_metadata: Optional task metadata to check rollback_ref.

        Returns:
            True if rollback is ready or not needed, False otherwise.
        """
        if not self.vault_path:
            return True

        rollback_dir = self.vault_path / 'Rollback_Archive'
        if not rollback_dir.exists():
            self._log_gate_blocked('rollback_readiness', 'rollback_archive_missing')
            return False

        return True

    def _log_gate_blocked(self, gate: str, detail: str) -> None:
        """Log a gate_blocked operation."""
        if self.ops_logger:
            self.ops_logger.log(
                op='gate_blocked',
                file='classifier',
                src=gate,
                outcome='flagged',
                detail=f'blocked:{detail}'
            )
