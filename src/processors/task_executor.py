"""
Task Executor for Gold Tier Foundation.

Executes task plan steps sequentially using a safe allowlist of operations.
Supports multi-step execution with per-step checkpoint logging and halt-on-failure.
All operations are file-system-only, no network, no destructive ops.
"""

import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


# Allowlist of safe operations
SAFE_OPERATIONS = {
    'file_create', 'file_copy', 'summarize',
    'create_folder', 'rename_file', 'move_file',
}


class TaskExecutor:
    """
    Executes task plan steps sequentially with per-step logging.

    Supported operations:
    - file_create: Create a new file with specified content
    - file_copy: Copy a file to a new location
    - summarize: Create a summary file from task content
    - create_folder: Create a new directory
    - rename_file: Rename a file
    - move_file: Move a file to a new location

    Multi-step execution: iterates ALL plan steps in order.
    Halt-on-failure: if step N fails, steps N+1..M are skipped.
    """

    def __init__(self, vault_path: Path, ops_logger=None):
        """
        Initialize TaskExecutor.

        Args:
            vault_path: Path to the Obsidian vault root.
            ops_logger: Optional OperationsLogger for per-step logging.
        """
        self.vault_path = Path(vault_path)
        self.ops_logger = ops_logger

    def execute(self, task_path: Path, plan_steps: list) -> dict:
        """
        Execute ALL plan steps sequentially with halt-on-failure.

        Args:
            task_path: Path to the task file.
            plan_steps: List of plan step strings.

        Returns:
            Dict with 'success', 'operation', 'detail', 'steps_executed',
            'steps_total', 'last_successful_step', 'step_results'.
        """
        result = {
            'success': False,
            'operation': 'multi_step',
            'detail': '',
            'steps_executed': 0,
            'steps_total': 0,
            'last_successful_step': -1,
            'step_results': [],
        }

        # Extract all actionable steps
        actionable_steps = self._get_all_actionable_steps(plan_steps)
        result['steps_total'] = len(actionable_steps)

        if not actionable_steps:
            result['detail'] = 'No actionable steps found'
            return result

        # Execute each step sequentially
        all_succeeded = True
        for i, step in enumerate(actionable_steps):
            step_num = i + 1
            op = self._detect_operation(step)

            step_result = {
                'step': step_num,
                'operation': op,
                'success': False,
                'detail': '',
            }

            try:
                if op == 'file_create':
                    step_result = self._execute_file_create(
                        task_path, step, step_result, step_num)
                elif op == 'file_copy':
                    step_result = self._execute_file_copy(
                        task_path, step, step_result, step_num)
                elif op == 'summarize':
                    step_result = self._execute_summarize(
                        task_path, step, step_result, step_num)
                elif op == 'create_folder':
                    step_result = self._execute_create_folder(
                        task_path, step, step_result, step_num)
                elif op == 'rename_file':
                    step_result = self._execute_rename_file(
                        task_path, step, step_result, step_num)
                elif op == 'move_file':
                    step_result = self._execute_move_file(
                        task_path, step, step_result, step_num)
                else:
                    step_result['detail'] = f'Operation not in allowlist: {op}'
            except Exception as e:
                step_result['success'] = False
                step_result['detail'] = f'Execution error: {str(e)}'
                logger.error(f"Step {step_num} failed for {task_path.name}: {e}")

            result['step_results'].append(step_result)
            result['steps_executed'] = step_num

            # Log per-step result
            self._log_step(task_path, step_num, step_result)

            if step_result['success']:
                result['last_successful_step'] = step_num
            else:
                # Halt-on-failure: skip remaining steps
                all_succeeded = False
                result['detail'] = (
                    f'Halted at step {step_num}/{len(actionable_steps)}: '
                    f'{step_result["detail"]}'
                )
                logger.warning(
                    f"Halt-on-failure: step {step_num} failed for {task_path.name}")
                break

        if all_succeeded:
            result['success'] = True
            result['detail'] = f'All {len(actionable_steps)} steps completed'
            if len(actionable_steps) == 1 and result['step_results']:
                result['operation'] = result['step_results'][0]['operation']
            else:
                result['operation'] = 'multi_step'

        return result

    def _get_all_actionable_steps(self, plan_steps: list) -> List[str]:
        """Get all non-empty, non-header steps."""
        actionable = []
        for step in plan_steps:
            cleaned = step.strip()
            if cleaned and not cleaned.startswith('#'):
                # Remove checkbox prefix if present
                cleaned = cleaned.lstrip('- ')
                if cleaned.startswith('[ ] '):
                    cleaned = cleaned[4:]
                elif cleaned.startswith('[x] '):
                    cleaned = cleaned[4:]
                if cleaned:
                    actionable.append(cleaned)
        return actionable

    def _get_first_actionable_step(self, plan_steps: list) -> Optional[str]:
        """Get the first non-empty, non-header step (backward compat)."""
        steps = self._get_all_actionable_steps(plan_steps)
        return steps[0] if steps else None

    def _detect_operation(self, step: str) -> str:
        """Detect which safe operation a step describes."""
        step_lower = step.lower()

        if any(kw in step_lower for kw in ['create file', 'create a file',
                                            'write file', 'new file']):
            return 'file_create'
        elif any(kw in step_lower for kw in ['create folder', 'create directory',
                                              'make directory', 'mkdir',
                                              'create a folder', 'new folder']):
            return 'create_folder'
        elif any(kw in step_lower for kw in ['rename file', 'rename the file',
                                              'rename a file']):
            return 'rename_file'
        elif any(kw in step_lower for kw in ['move file', 'move the file',
                                              'move a file']):
            return 'move_file'
        elif any(kw in step_lower for kw in ['copy file', 'copy the file',
                                              'duplicate']):
            return 'file_copy'
        elif any(kw in step_lower for kw in ['summar', 'create summary',
                                              'generate summary']):
            return 'summarize'
        else:
            return 'unknown'

    def _log_step(self, task_path: Path, step_num: int,
                  step_result: dict) -> None:
        """Log per-step execution result to operations logger."""
        if self.ops_logger:
            self.ops_logger.log(
                op='step_executed',
                file=task_path.name,
                src='In_Progress',
                outcome='success' if step_result['success'] else 'failed',
                detail=(
                    f"step {step_num}: op={step_result['operation']} "
                    f"success={step_result['success']} "
                    f"detail={step_result['detail']}"
                )
            )

    def _execute_file_create(self, task_path: Path, step: str,
                             result: dict, step_num: int = 1) -> dict:
        """Execute a file_create operation."""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_name = f"output-{timestamp}-s{step_num}-{task_path.stem}.md"
        output_path = self.vault_path / 'In_Progress' / output_name

        content = f"# Auto-Generated Output\n\n"
        content += f"**Source Task**: {task_path.name}\n"
        content += f"**Generated**: {datetime.now().isoformat()}\n"
        content += f"**Step**: {step_num}\n\n"
        content += f"## Step Executed\n\n{step}\n"

        output_path.write_text(content, encoding='utf-8')
        result['success'] = True
        result['detail'] = f'Created: {output_name}'
        logger.info(f"file_create executed (step {step_num}): {output_name}")
        return result

    def _execute_file_copy(self, task_path: Path, step: str,
                           result: dict, step_num: int = 1) -> dict:
        """Execute a file_copy operation."""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        copy_name = f"copy-{timestamp}-s{step_num}-{task_path.name}"
        copy_path = self.vault_path / 'In_Progress' / copy_name

        if task_path.exists():
            shutil.copy2(str(task_path), str(copy_path))
            result['success'] = True
            result['detail'] = f'Copied: {copy_name}'
            logger.info(f"file_copy executed (step {step_num}): {copy_name}")
        else:
            result['detail'] = f'Source file not found: {task_path}'
        return result

    def _execute_summarize(self, task_path: Path, step: str,
                           result: dict, step_num: int = 1) -> dict:
        """Execute a summarize operation."""
        try:
            task_content = task_path.read_text(encoding='utf-8')
        except Exception:
            result['detail'] = f'Could not read task: {task_path}'
            return result

        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        summary_name = f"summary-{timestamp}-s{step_num}-{task_path.stem}.md"
        summary_path = self.vault_path / 'In_Progress' / summary_name

        lines = task_content.split('\n')
        summary_lines = [l for l in lines if l.startswith('#') or
                         l.startswith('- **')]

        content = f"# Summary: {task_path.name}\n\n"
        content += f"**Generated**: {datetime.now().isoformat()}\n"
        content += f"**Step**: {step_num}\n\n"
        content += "## Key Points\n\n"
        content += '\n'.join(summary_lines[:20]) + '\n'

        summary_path.write_text(content, encoding='utf-8')
        result['success'] = True
        result['detail'] = f'Summarized: {summary_name}'
        logger.info(f"summarize executed (step {step_num}): {summary_name}")
        return result

    def _execute_create_folder(self, task_path: Path, step: str,
                               result: dict, step_num: int = 1) -> dict:
        """Execute a create_folder operation."""
        # Extract folder name from step text
        folder_name = self._extract_name_from_step(step, 'folder')
        if not folder_name:
            folder_name = f"folder-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        folder_path = self.vault_path / 'In_Progress' / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        result['success'] = True
        result['detail'] = f'Created folder: {folder_name}'
        logger.info(f"create_folder executed (step {step_num}): {folder_name}")
        return result

    def _execute_rename_file(self, task_path: Path, step: str,
                             result: dict, step_num: int = 1) -> dict:
        """Execute a rename_file operation."""
        new_name = self._extract_name_from_step(step, 'file')
        if not new_name:
            result['detail'] = 'Could not determine new filename from step'
            return result

        if task_path.exists():
            new_path = task_path.parent / new_name
            task_path.rename(new_path)
            result['success'] = True
            result['detail'] = f'Renamed to: {new_name}'
            logger.info(f"rename_file executed (step {step_num}): {new_name}")
        else:
            result['detail'] = f'Source file not found: {task_path}'
        return result

    def _execute_move_file(self, task_path: Path, step: str,
                           result: dict, step_num: int = 1) -> dict:
        """Execute a move_file operation."""
        # Move file within vault (default: to Done)
        if task_path.exists():
            dest = self.vault_path / 'Done' / task_path.name
            shutil.move(str(task_path), str(dest))
            result['success'] = True
            result['detail'] = f'Moved: {task_path.name} -> Done/'
            logger.info(f"move_file executed (step {step_num}): {task_path.name}")
        else:
            result['detail'] = f'Source file not found: {task_path}'
        return result

    def _extract_name_from_step(self, step: str, entity: str) -> Optional[str]:
        """Extract a name (file/folder) from a step description."""
        import re
        # Try to find quoted names
        quoted = re.findall(r'["\']([^"\']+)["\']', step)
        if quoted:
            return quoted[0]

        # Try to find names after "named" or "called"
        named = re.search(r'(?:named|called)\s+(\S+)', step, re.IGNORECASE)
        if named:
            return named.group(1)

        return None
