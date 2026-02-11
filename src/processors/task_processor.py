"""
Task Processor for Gold Tier Foundation.

Reads tasks from /Needs_Action and generates action plans using Claude.
Plans are saved to /Plans with checkbox-formatted steps.
Classifies tasks using 6-gate system, auto-executes simple/complex ones,
integrates rollback, SLA tracking, and notifications.
"""

import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import frontmatter

from utils.vault_manager import VaultManager
from utils.config import get_config
from processors.task_classifier import TaskClassifier
from processors.task_executor import TaskExecutor
from orchestrator.rollback_manager import RollbackManager
from processors.branch_router import BranchRouter
from notifications.notifier import NoOpNotifier

logger = logging.getLogger(__name__)


# Plan template
PLAN_TEMPLATE = """# Plan: {title}

**Source Task**: [[Needs_Action/{task_filename}]]
**Generated**: {timestamp}

## Action Steps

{steps}

## Notes

{notes}
"""


class TaskProcessor:
    """
    Processes tasks and generates action plans using Claude.

    Reads pending tasks from /Needs_Action, uses Claude Code CLI
    to generate plans, and saves them to /Plans.
    """

    def __init__(self, vault_path: Path, ops_logger=None,
                 notifier=None, sla_tracker=None):
        """
        Initialize the TaskProcessor.

        Args:
            vault_path: Path to the Obsidian vault root.
            ops_logger: Optional OperationsLogger for audit trail.
            notifier: Optional Notifier for status change notifications.
            sla_tracker: Optional SLATracker for compliance tracking.
        """
        self.vault_path = Path(vault_path)
        self.vault_manager = VaultManager(vault_path)
        self.plans_path = self.vault_path / 'Plans'
        self.classifier = TaskClassifier(vault_path=vault_path, ops_logger=ops_logger)
        self.executor = TaskExecutor(vault_path, ops_logger=ops_logger)
        self.ops_logger = ops_logger
        self.notifier = notifier or NoOpNotifier()
        self.sla_tracker = sla_tracker
        self.branch_router = BranchRouter()
        config = get_config()
        self.rollback_manager = RollbackManager(
            vault_path,
            ops_logger=ops_logger,
            retention_days=config.get('rollback_retention_days', 7)
        )
        self._processed_tasks: set = set()

    def read_pending_tasks(self) -> List[Path]:
        """
        Get list of pending tasks from /Needs_Action.

        Returns:
            List of Path objects for pending task files.
        """
        return self.vault_manager.get_pending_tasks()

    def suggest_execution_sequence(self, pending_tasks: List[Path]) -> List[Path]:
        """
        Suggest execution order: critical tasks first, then by creation time.

        Args:
            pending_tasks: List of task file paths.

        Returns:
            Sorted list of task paths (critical first, then oldest first).
        """
        def sort_key(path: Path):
            priority_val = 2  # default normal
            created = float('inf')
            try:
                post = self.vault_manager.read_file(f"Needs_Action/{path.name}")
                if post:
                    priority = post.metadata.get('priority', 'normal')
                    priority_val = self.branch_router.get_priority_value(priority)
                created = path.stat().st_ctime
            except Exception:
                pass
            # Negate priority so higher priority comes first
            return (-priority_val, created)

        return sorted(pending_tasks, key=sort_key)

    def classify_and_execute(self, task_path: Path,
                             plan_steps: str) -> Optional[dict]:
        """
        Classify a task and conditionally execute if simple.

        Args:
            task_path: Path to the task file.
            plan_steps: Raw plan steps string.

        Returns:
            Dict with classification and execution result, or None.
        """
        steps_list = [s.strip() for s in plan_steps.split('\n') if s.strip()]
        task_content = ''
        task_metadata = None

        try:
            task_content = task_path.read_text(encoding='utf-8')
            post = self.vault_manager.read_file(f"Needs_Action/{task_path.name}")
            if post:
                task_metadata = dict(post.metadata)
        except Exception:
            pass

        classification = self.classifier.classify(
            task_content, steps_list, task_metadata=task_metadata
        )
        gate_results = self.classifier.get_gate_results()

        result = {
            'classification': classification,
            'executed': False,
            'execution_result': None,
            'gate_results': gate_results,
        }

        # Update task frontmatter with classification and gate results
        self._update_task_classification(task_path, classification, gate_results)

        config = get_config()
        auto_execute_simple = config.get('auto_execute_simple', False)
        auto_execute_complex = config.get('auto_execute_complex', False)
        src_folder = 'In_Progress' if 'In_Progress' in str(task_path) else 'Needs_Action'

        # Log classification
        if self.ops_logger:
            self.ops_logger.log(
                op='task_classified',
                file=task_path.name,
                src=src_folder,
                outcome='success',
                detail=f'complexity:{classification}'
            )

        # Determine if we should execute
        should_execute = False
        if classification == 'simple' and auto_execute_simple:
            should_execute = True
        elif classification == 'complex' and auto_execute_complex:
            should_execute = True

        if should_execute:
            # Move task to in_progress before execution
            self._update_task_status(task_path, 'in_progress')

            # Create rollback snapshot for complex tasks
            snapshot_dir = None
            if classification == 'complex':
                task_file = self._find_task_file(task_path)
                if task_file:
                    snapshot_dir = self.rollback_manager.create_snapshot(task_file)
                    if not snapshot_dir:
                        # Snapshot failed — block execution
                        self._update_task_status(task_path, 'blocked')
                        result['execution_result'] = {
                            'success': False,
                            'detail': 'rollback_snapshot_failed'
                        }
                        self._append_execution_log(task_path, result['execution_result'])
                        return result
                    # Write rollback_ref to frontmatter
                    self._update_task_rollback_ref(task_path, str(snapshot_dir))

            exec_result = self.executor.execute(task_path, steps_list)
            result['executed'] = True
            result['execution_result'] = exec_result

            if exec_result.get('success'):
                self._update_task_status(task_path, 'done')
            else:
                # On failure, attempt rollback for complex tasks
                if classification == 'complex' and snapshot_dir:
                    task_file = self._find_task_file(task_path)
                    if task_file:
                        self.rollback_manager.restore_snapshot(snapshot_dir, task_file)
                else:
                    self._update_task_status(task_path, 'failed')

            if self.ops_logger:
                self.ops_logger.log(
                    op='task_executed',
                    file=task_path.name,
                    src=src_folder,
                    outcome='success' if exec_result.get('success') else 'failed',
                    detail=f"op:{exec_result.get('operation', 'unknown')} complexity:{classification}"
                )

            # Append execution log to task file
            self._append_execution_log(task_path, exec_result)

        return result

    def _update_task_status(self, task_path: Path, new_status: str) -> None:
        """Update task frontmatter status field, increment version, notify, and check SLA."""
        try:
            for folder in ['In_Progress', 'Needs_Action']:
                rel = f"{folder}/{task_path.name}"
                if self.vault_manager.file_exists(rel):
                    post = self.vault_manager.read_file(rel)
                    if post:
                        old_status = post.metadata.get('status', 'pending')
                        post.metadata['status'] = new_status
                        post.metadata['updated'] = datetime.now().isoformat()
                        post.metadata['version'] = post.metadata.get('version', 1) + 1
                        if new_status in ('done', 'failed', 'failed_rollback'):
                            post.metadata['completed_at'] = datetime.now().isoformat()
                        file_path = self.vault_path / rel
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))
                        logger.info(f"Updated task status to '{new_status}' (v{post.metadata['version']}): {task_path.name}")

                        # Send notification on status transition
                        self.notifier.send({
                            'task_name': task_path.name,
                            'old_status': old_status,
                            'new_status': new_status,
                            'timestamp': datetime.now().isoformat(),
                            'severity': 'critical' if new_status in ('failed', 'failed_rollback') else 'info',
                        })

                        # Check SLA on terminal statuses
                        if new_status in ('done', 'failed') and self.sla_tracker:
                            self.sla_tracker.check_sla(file_path)
                    return
        except Exception as e:
            logger.error(f"Error updating task status: {e}")

    def _find_task_file(self, task_path: Path) -> Optional[Path]:
        """Find the actual task file in vault folders."""
        for folder in ['In_Progress', 'Needs_Action']:
            full_path = self.vault_path / folder / task_path.name
            if full_path.exists():
                return full_path
        return None

    def _update_task_rollback_ref(self, task_path: Path, rollback_ref: str) -> None:
        """Write rollback_ref field to task frontmatter."""
        try:
            for folder in ['In_Progress', 'Needs_Action']:
                rel = f"{folder}/{task_path.name}"
                if self.vault_manager.file_exists(rel):
                    post = self.vault_manager.read_file(rel)
                    if post:
                        post.metadata['rollback_ref'] = rollback_ref
                        file_path = self.vault_path / rel
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))
                    return
        except Exception as e:
            logger.error(f"Error updating rollback_ref: {e}")

    def _update_task_classification(self, task_path: Path,
                                     classification: str,
                                     gate_results: Optional[dict] = None) -> None:
        """Update task frontmatter with classification and gate results."""
        try:
            for folder in ['In_Progress', 'Needs_Action']:
                rel = f"{folder}/{task_path.name}"
                if self.vault_manager.file_exists(rel):
                    post = self.vault_manager.read_file(rel)
                    if post:
                        post.metadata['complexity'] = classification
                        post.metadata['classified_at'] = datetime.now().isoformat()
                        if gate_results:
                            post.metadata['gate_results'] = gate_results
                        file_path = self.vault_path / rel
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))
                    break
        except Exception as e:
            logger.error(f"Error updating classification: {e}")

    def _append_execution_log(self, task_path: Path,
                               exec_result: dict) -> None:
        """Append execution log entries to task file (supports multi-step)."""
        try:
            for folder in ['In_Progress', 'Needs_Action']:
                full_path = self.vault_path / folder / task_path.name
                if full_path.exists():
                    content = full_path.read_text(encoding='utf-8')
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # Build log entries
                    log_lines = []
                    step_results = exec_result.get('step_results', [])
                    if step_results:
                        for sr in step_results:
                            log_lines.append(
                                f"- {timestamp}: step {sr['step']}: "
                                f"op={sr['operation']} success={sr['success']} "
                                f"detail={sr['detail']}"
                            )
                    else:
                        success = exec_result.get('success', False)
                        op = exec_result.get('operation', 'unknown')
                        detail = exec_result.get('detail', '')
                        log_lines.append(
                            f"- {timestamp}: op={op} "
                            f"success={success} detail={detail}"
                        )

                    log_entry = '\n'.join(log_lines)

                    if '## Execution Log' in content:
                        content = content.replace(
                            '## Execution Log\n',
                            f'## Execution Log\n\n{log_entry}\n'
                        )
                    else:
                        content += f"\n\n## Execution Log\n\n{log_entry}\n"

                    full_path.write_text(content, encoding='utf-8')
                    break
        except Exception as e:
            logger.error(f"Error appending execution log: {e}")

    def process_task(self, task_path: Path) -> Optional[Path]:
        """
        Process a single task: generate plan, classify, and optionally execute.

        Args:
            task_path: Path to the task file.

        Returns:
            Path to generated plan file, or None if failed.
        """
        logger.info(f"Processing task: {task_path.name}")

        # Read task content
        post = self.vault_manager.read_file(f"Needs_Action/{task_path.name}")
        if post is None:
            logger.error(f"Could not read task: {task_path}")
            return None

        # Extract task info
        task_title = self._extract_title(post.content)
        task_content = post.content

        # Generate plan using Claude
        plan_steps = self.generate_plan(task_title, task_content)
        if not plan_steps:
            logger.error(f"Failed to generate plan for: {task_path.name}")
            return None

        # Format and save plan
        plan_path = self.write_plan(
            task_filename=task_path.name,
            title=task_title,
            steps=plan_steps,
            notes="Generated automatically by Silver Tier task processor."
        )

        if plan_path:
            self.link_task_to_plan(task_path, plan_path)
            if self.ops_logger:
                self.ops_logger.log(
                    op='plan_generated',
                    file=task_path.name,
                    src='Needs_Action',
                    dst='Plans',
                    outcome='success',
                    detail=f'plan:{plan_path.name}'
                )

        # Classify and conditionally execute
        classify_result = self.classify_and_execute(task_path, plan_steps)
        if classify_result:
            logger.info(
                f"Task {task_path.name}: "
                f"classification={classify_result['classification']}, "
                f"executed={classify_result['executed']}"
            )

        return plan_path

    def _extract_title(self, content: str) -> str:
        """
        Extract title from task content.

        Looks for '# Task: ...' heading.

        Args:
            content: Task markdown content.

        Returns:
            Extracted title or 'Untitled Task'.
        """
        for line in content.split('\n'):
            if line.startswith('# Task:'):
                return line.replace('# Task:', '').strip()
        return 'Untitled Task'

    def generate_plan(self, title: str, content: str) -> Optional[str]:
        """
        Generate action plan steps using Claude CLI.

        Args:
            title: Task title.
            content: Task content.

        Returns:
            Formatted plan steps as markdown, or None if failed.
        """
        prompt = f"""Generate an action plan for the following task.
The plan must:
1. Have at least 3 actionable steps
2. Use checkbox format (- [ ] Step description)
3. Be written in plain, professional language
4. Be understandable without technical knowledge

Task Title: {title}

Task Content:
{content[:2000]}

Output ONLY the action steps in checkbox format, nothing else:"""

        try:
            # Try using Claude CLI
            result = subprocess.run(
                ['claude', '--print', '-p', prompt],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and result.stdout.strip():
                steps = result.stdout.strip()
                # Validate steps format
                if self._validate_steps(steps):
                    logger.info("Generated plan using Claude CLI")
                    return steps
                else:
                    logger.warning("Claude output didn't match expected format")

        except FileNotFoundError:
            logger.warning("Claude CLI not found, using fallback plan generation")
        except subprocess.TimeoutExpired:
            logger.error("Claude CLI timed out")
        except Exception as e:
            logger.error(f"Error calling Claude CLI: {e}")

        # Fallback: generate basic plan
        return self._generate_fallback_plan(title, content)

    def _validate_steps(self, steps: str) -> bool:
        """
        Validate that steps are in checkbox format.

        Args:
            steps: Generated steps text.

        Returns:
            True if at least 3 checkbox steps found.
        """
        checkbox_count = steps.count('- [ ]')
        return checkbox_count >= 3

    def _generate_fallback_plan(self, title: str, content: str) -> str:
        """
        Generate a basic fallback plan when Claude is unavailable.

        Args:
            title: Task title.
            content: Task content.

        Returns:
            Fallback plan steps.
        """
        logger.info("Using fallback plan generation")
        return f"""- [ ] Review the task: {title}
- [ ] Identify required actions and resources
- [ ] Execute the primary action for this task
- [ ] Verify completion and document results
- [ ] Move task to Done folder when complete"""

    def write_plan(self, task_filename: str, title: str,
                   steps: str, notes: str = "") -> Optional[Path]:
        """
        Write a plan file to /Plans.

        Args:
            task_filename: Original task filename (for linking).
            title: Plan title.
            steps: Checkbox-formatted action steps.
            notes: Optional additional notes.

        Returns:
            Path to created plan file, or None if failed.
        """
        # Generate plan filename
        plan_filename = task_filename.replace('.md', '-plan.md')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Format plan content
        content = PLAN_TEMPLATE.format(
            title=title,
            task_filename=task_filename,
            timestamp=timestamp,
            steps=steps,
            notes=notes
        )

        # Add frontmatter
        metadata = {
            'plan_id': f"plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'task_ref': task_filename,
            'generated': datetime.now().isoformat(),
            'generator': 'claude-code',
            'step_count': steps.count('- [ ]')
        }

        plan_path = self.plans_path / plan_filename

        try:
            post = frontmatter.Post(content, **metadata)
            with open(plan_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))

            logger.info(f"Created plan: {plan_path}")
            print(f"📋 Generated plan: {plan_filename}")
            return plan_path
        except Exception as e:
            logger.error(f"Error writing plan: {e}")
            return None

    def link_task_to_plan(self, task_path: Path, plan_path: Path) -> bool:
        """
        Update task to link to its generated plan.

        Adds plan reference to task metadata.

        Args:
            task_path: Path to the task file.
            plan_path: Path to the generated plan file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            relative_task_path = f"Needs_Action/{task_path.name}"
            post = self.vault_manager.read_file(relative_task_path)
            if post is None:
                return False

            post.metadata['plan_ref'] = plan_path.name
            post.metadata['plan_generated'] = datetime.now().isoformat()

            file_path = self.vault_path / relative_task_path
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))

            logger.debug(f"Linked task to plan: {task_path.name} -> {plan_path.name}")
            return True
        except Exception as e:
            logger.error(f"Error linking task to plan: {e}")
            return False

    def process_all_pending(self) -> int:
        """
        Process all pending tasks that don't have plans.

        Returns:
            Number of plans generated.
        """
        pending_tasks = self.read_pending_tasks()
        plans_generated = 0

        for task_path in pending_tasks:
            # Skip if already processed in this session
            if task_path.name in self._processed_tasks:
                continue

            # Check if plan already exists
            plan_filename = task_path.name.replace('.md', '-plan.md')
            if (self.plans_path / plan_filename).exists():
                logger.debug(f"Plan already exists for: {task_path.name}")
                self._processed_tasks.add(task_path.name)
                continue

            # Process the task
            plan_path = self.process_task(task_path)
            if plan_path:
                plans_generated += 1
                self._processed_tasks.add(task_path.name)

        return plans_generated
