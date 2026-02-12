"""
Dashboard Updater for Silver Tier Foundation.

Updates Dashboard.md with current statistics, metrics, and activity log.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import frontmatter as fm_lib

from utils.vault_manager import VaultManager

logger = logging.getLogger(__name__)


# Gold Tier Dashboard template
DASHBOARD_TEMPLATE = """# Dashboard

**Last Updated**: {timestamp}
**Last Active**: {last_active}

## Recent Activity

{activity_log}

## Statistics

- **Pending Tasks**: {pending_count}
- **In-Progress Tasks**: {in_progress_count}
- **Completed Today**: {completed_today}
- **Completed All-Time**: {completed_count}
- **Plans Generated**: {plans_count}

## Metrics

- **Average Completion Time**: {avg_completion_time}
- **Error Rate (24h)**: {error_rate}
- **Rollback Incidents (24h)**: {rollback_count}
- **SLA Compliance (24h)**: {sla_compliance}
- **Throughput (24h)**: {throughput}

## Platinum Intelligence

- **Predictive SLA Alerts (24h)**: {sla_predictions}
- **Self-Healing Recoveries (24h)**: {self_heal_count}
- **Risk Score Distribution**: {risk_distribution}
- **Learning Data Points**: {learning_points}

## Active Alerts

{active_alerts}

## Recent Errors

{recent_errors}

## Watcher Status

{watcher_status}
"""

# Alert severity definitions
ALERT_TRIGGERS = {
    'task_executed': {'outcome': 'failed', 'severity': 'critical', 'label': 'Execution failure'},
    'sla_breach': {'outcome': 'flagged', 'severity': 'warning', 'label': 'SLA breach'},
    'credential_flagged': {'outcome': 'flagged', 'severity': 'critical', 'label': 'Credential detected'},
    'rollback_triggered': {'outcome': 'failed', 'severity': 'warning', 'label': 'Rollback triggered'},
    'heartbeat_fail': {'outcome': 'failed', 'severity': 'critical', 'label': 'Heartbeat failure'},
}


class DashboardUpdater:
    """
    Updates the Dashboard.md file with current statistics and metrics.

    Maintains:
    - Recent activity log (last 10 entries)
    - Task counts (pending, in-progress, completed, plans)
    - Average completion time, error rate
    - Watcher status
    """

    MAX_ACTIVITY_ENTRIES = 10

    def __init__(self, vault_path: Path, ops_logger=None):
        """
        Initialize the DashboardUpdater.

        Args:
            vault_path: Path to the Obsidian vault root.
            ops_logger: Optional OperationsLogger for metrics.
        """
        self.vault_path = Path(vault_path)
        self.dashboard_path = self.vault_path / 'Dashboard.md'
        self.vault_manager = VaultManager(vault_path)
        self.ops_logger = ops_logger
        self._activity_log: List[str] = []
        self._load_existing_activity()

    def _load_existing_activity(self) -> None:
        """Load existing activity entries from Dashboard.md."""
        if not self.dashboard_path.exists():
            return

        try:
            content = self.dashboard_path.read_text(encoding='utf-8')

            # Find activity section
            in_activity = False
            for line in content.split('\n'):
                if '## Recent Activity' in line:
                    in_activity = True
                    continue
                elif line.startswith('##') and in_activity:
                    break
                elif in_activity and line.startswith('- '):
                    self._activity_log.append(line[2:])  # Remove '- ' prefix

            # Keep only last N entries
            self._activity_log = self._activity_log[-self.MAX_ACTIVITY_ENTRIES:]
            logger.debug(f"Loaded {len(self._activity_log)} activity entries")
        except Exception as e:
            logger.error(f"Error loading activity log: {e}")

    def count_pending_tasks(self) -> int:
        """Count pending tasks in /Needs_Action."""
        return len(self.vault_manager.get_pending_tasks())

    def count_in_progress_tasks(self) -> int:
        """Count in-progress tasks in /In_Progress."""
        return len(self.vault_manager.get_in_progress_tasks())

    def count_completed_tasks(self) -> int:
        """Count completed tasks in /Done."""
        return len(self.vault_manager.get_completed_tasks())

    def count_completed_today(self) -> int:
        """Count tasks completed today (by file modified date)."""
        today = datetime.now().date()
        count = 0
        for task in self.vault_manager.get_completed_tasks():
            try:
                mtime = datetime.fromtimestamp(task.stat().st_mtime).date()
                if mtime == today:
                    count += 1
            except Exception:
                pass
        return count

    def count_plans(self) -> int:
        """Count generated plans in /Plans."""
        return len(self.vault_manager.get_plans())

    def calculate_avg_completion_time(self) -> str:
        """
        Calculate average completion time from Done task frontmatter.

        Reads 'created' and 'updated' timestamps from /Done/ files.

        Returns:
            Human-readable average time string.
        """
        deltas = []
        for task_path in self.vault_manager.get_completed_tasks():
            try:
                with open(task_path, 'r', encoding='utf-8') as f:
                    post = fm_lib.load(f)
                created = post.metadata.get('created')
                updated = post.metadata.get('updated')
                if created and updated:
                    created_dt = datetime.fromisoformat(str(created))
                    updated_dt = datetime.fromisoformat(str(updated))
                    delta = (updated_dt - created_dt).total_seconds()
                    if delta > 0:
                        deltas.append(delta)
            except Exception:
                continue

        if not deltas:
            return "N/A"

        avg_seconds = sum(deltas) / len(deltas)
        if avg_seconds < 60:
            return f"{avg_seconds:.0f}s"
        elif avg_seconds < 3600:
            return f"{avg_seconds / 60:.1f}m"
        else:
            return f"{avg_seconds / 3600:.1f}h"

    def calculate_error_rate(self, hours: int = 24) -> str:
        """
        Calculate error rate from OperationsLogger.

        Args:
            hours: Time window (default: 24).

        Returns:
            Error rate as string (e.g., "2 errors in 24h").
        """
        if not self.ops_logger:
            return "N/A (no logger)"

        count = self.ops_logger.count_errors(hours)
        return f"{count} error(s) in {hours}h"

    def get_recent_errors(self, n: int = 5) -> str:
        """
        Get formatted recent errors.

        Args:
            n: Number of errors to show.

        Returns:
            Markdown-formatted error list.
        """
        if not self.ops_logger:
            return "- No error logger configured"

        errors = self.ops_logger.get_errors(n)
        if not errors:
            return "- No recent errors"

        lines = []
        for err in errors:
            ts = err.get('ts', 'unknown')
            detail = err.get('detail', 'no detail')
            file = err.get('file', 'unknown')
            lines.append(f"- {ts}: {file} — {detail}")
        return '\n'.join(lines)

    def add_activity_entry(self, message: str) -> None:
        """
        Add a new activity entry.

        Maintains a maximum of MAX_ACTIVITY_ENTRIES entries.

        Args:
            message: Activity message to add.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        entry = f"{timestamp}: {message}"

        self._activity_log.append(entry)

        # Keep only last N entries
        if len(self._activity_log) > self.MAX_ACTIVITY_ENTRIES:
            self._activity_log = self._activity_log[-self.MAX_ACTIVITY_ENTRIES:]

        logger.debug(f"Added activity: {entry}")

    def get_activity_log(self) -> str:
        """
        Get formatted activity log.

        Returns:
            Markdown-formatted activity list.
        """
        if not self._activity_log:
            return "- No recent activity"

        # Return newest first
        entries = list(reversed(self._activity_log))
        return '\n'.join(f"- {entry}" for entry in entries)

    def count_rollback_incidents(self, hours: int = 24) -> int:
        """Count rollback_triggered events in the last N hours."""
        if not self.ops_logger:
            return 0
        recent = self.ops_logger.read_recent(200)
        cutoff = datetime.now().timestamp() - (hours * 3600)
        count = 0
        for entry in recent:
            if entry.get('op') == 'rollback_triggered':
                try:
                    ts_str = entry.get('ts', '')
                    ts = datetime.fromisoformat(
                        ts_str.replace('.', ':', 2) if ts_str.count('.') > 1 else ts_str
                    )
                    if ts.timestamp() >= cutoff:
                        count += 1
                except (ValueError, TypeError):
                    count += 1
        return count

    def compute_sla_compliance(self, hours: int = 24) -> str:
        """Compute SLA compliance % from ops log."""
        if not self.ops_logger:
            return "N/A"
        recent = self.ops_logger.read_recent(200)
        cutoff = datetime.now().timestamp() - (hours * 3600)
        executed = 0
        breached = 0
        for entry in recent:
            try:
                ts_str = entry.get('ts', '')
                ts = datetime.fromisoformat(
                    ts_str.replace('.', ':', 2) if ts_str.count('.') > 1 else ts_str
                )
                if ts.timestamp() < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            if entry.get('op') == 'task_executed':
                executed += 1
            elif entry.get('op') == 'sla_breach':
                breached += 1
        if executed == 0:
            return "100.0% (0 tasks)"
        pct = ((executed - breached) / executed) * 100
        return f"{pct:.1f}% ({executed} tasks)"

    def compute_throughput(self, hours: int = 24) -> str:
        """Compute tasks/hour throughput from ops log."""
        if not self.ops_logger:
            return "N/A"
        recent = self.ops_logger.read_recent(200)
        cutoff = datetime.now().timestamp() - (hours * 3600)
        completed = 0
        for entry in recent:
            if entry.get('op') == 'task_executed' and entry.get('outcome') == 'success':
                try:
                    ts_str = entry.get('ts', '')
                    ts = datetime.fromisoformat(
                        ts_str.replace('.', ':', 2) if ts_str.count('.') > 1 else ts_str
                    )
                    if ts.timestamp() >= cutoff:
                        completed += 1
                except (ValueError, TypeError):
                    completed += 1
        rate = completed / hours if hours > 0 else 0
        return f"{rate:.1f} tasks/hour ({completed} in {hours}h)"

    def compute_active_alerts(self, n: int = 10) -> str:
        """Compute active alerts from recent ops log events."""
        if not self.ops_logger:
            return "- No alerts (logger not configured)"
        recent = self.ops_logger.read_recent(100)
        alerts = []
        for entry in recent:
            op = entry.get('op', '')
            outcome = entry.get('outcome', '')
            if op in ALERT_TRIGGERS:
                trigger = ALERT_TRIGGERS[op]
                if outcome == trigger['outcome'] or trigger['outcome'] == '*':
                    severity = trigger['severity']
                    label = trigger['label']
                    ts = entry.get('ts', 'unknown')
                    file_name = entry.get('file', 'unknown')
                    icon = '🔴' if severity == 'critical' else '🟡'
                    alerts.append(f"- {icon} **[{severity.upper()}]** {ts}: {label} — {file_name}")
            if len(alerts) >= n:
                break
        if not alerts:
            return "- No active alerts"
        return '\n'.join(alerts)

    def count_sla_predictions(self, hours: int = 24) -> str:
        """Count predictive SLA alerts in the last N hours."""
        if not self.ops_logger:
            return "N/A"
        recent = self.ops_logger.read_recent(200)
        cutoff = datetime.now().timestamp() - (hours * 3600)
        count = 0
        for entry in recent:
            if entry.get('op') == 'sla_prediction':
                try:
                    ts_str = entry.get('ts', '')
                    ts = datetime.fromisoformat(
                        ts_str.replace('.', ':', 2) if ts_str.count('.') > 1 else ts_str
                    )
                    if ts.timestamp() >= cutoff:
                        count += 1
                except (ValueError, TypeError):
                    count += 1
        return f"{count} alert(s)"

    def count_self_heal_recoveries(self, hours: int = 24) -> str:
        """Count successful self-healing recoveries in the last N hours."""
        if not self.ops_logger:
            return "N/A"
        recent = self.ops_logger.read_recent(200)
        cutoff = datetime.now().timestamp() - (hours * 3600)
        healed = 0
        attempted = 0
        for entry in recent:
            op = entry.get('op', '')
            if op.startswith('self_heal_'):
                try:
                    ts_str = entry.get('ts', '')
                    ts = datetime.fromisoformat(
                        ts_str.replace('.', ':', 2) if ts_str.count('.') > 1 else ts_str
                    )
                    if ts.timestamp() >= cutoff:
                        attempted += 1
                        if entry.get('outcome') == 'success':
                            healed += 1
                except (ValueError, TypeError):
                    attempted += 1
        return f"{healed}/{attempted} successful"

    def compute_risk_distribution(self) -> str:
        """Compute risk score distribution from recent risk_scored events."""
        if not self.ops_logger:
            return "N/A"
        recent = self.ops_logger.read_recent(200)
        high = med = low = 0
        for entry in recent:
            if entry.get('op') == 'risk_scored':
                detail = entry.get('detail', '')
                try:
                    for part in detail.split():
                        if part.startswith('composite='):
                            score = float(part.split('=')[1])
                            if score > 0.7:
                                high += 1
                            elif score > 0.4:
                                med += 1
                            else:
                                low += 1
                            break
                except (ValueError, IndexError):
                    pass
        return f"High:{high} Med:{med} Low:{low}"

    def count_learning_points(self) -> str:
        """Count total learning data points from Learning_Data folder."""
        ld = self.vault_path / 'Learning_Data'
        if not ld.exists():
            return "0"
        count = 0
        for f in ld.glob('*.jsonl'):
            try:
                count += sum(1 for _ in f.read_text().strip().split('\n') if _.strip())
            except Exception:
                pass
        return str(count)

    def get_watcher_status(self, file_watcher_running: bool = False,
                           gmail_configured: bool = False) -> str:
        """
        Get formatted watcher status.

        Args:
            file_watcher_running: Whether file watcher is active.
            gmail_configured: Whether Gmail watcher is configured.

        Returns:
            Markdown-formatted watcher status.
        """
        file_status = "Running" if file_watcher_running else "Stopped"
        gmail_status = "Configured" if gmail_configured else "Not configured"

        return f"""- **File Watcher**: {file_status}
- **Gmail Watcher**: {gmail_status}"""

    def refresh_dashboard(self, file_watcher_running: bool = False,
                          gmail_configured: bool = False) -> bool:
        """
        Refresh Dashboard.md with current statistics and metrics.

        Args:
            file_watcher_running: Whether file watcher is active.
            gmail_configured: Whether Gmail watcher is configured.

        Returns:
            True if successful, False otherwise.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        content = DASHBOARD_TEMPLATE.format(
            timestamp=timestamp,
            last_active=timestamp,
            activity_log=self.get_activity_log(),
            pending_count=self.count_pending_tasks(),
            in_progress_count=self.count_in_progress_tasks(),
            completed_today=self.count_completed_today(),
            completed_count=self.count_completed_tasks(),
            plans_count=self.count_plans(),
            avg_completion_time=self.calculate_avg_completion_time(),
            error_rate=self.calculate_error_rate(),
            rollback_count=self.count_rollback_incidents(),
            sla_compliance=self.compute_sla_compliance(),
            throughput=self.compute_throughput(),
            sla_predictions=self.count_sla_predictions(),
            self_heal_count=self.count_self_heal_recoveries(),
            risk_distribution=self.compute_risk_distribution(),
            learning_points=self.count_learning_points(),
            active_alerts=self.compute_active_alerts(),
            recent_errors=self.get_recent_errors(),
            watcher_status=self.get_watcher_status(
                file_watcher_running, gmail_configured
            )
        )

        try:
            self.dashboard_path.write_text(content, encoding='utf-8')
            logger.info("Dashboard refreshed")
            return True
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {e}")
            return False

    def update(self, activity_message: Optional[str] = None) -> bool:
        """
        Update dashboard with optional new activity entry.

        Args:
            activity_message: Optional message to add to activity log.

        Returns:
            True if successful, False otherwise.
        """
        if activity_message:
            self.add_activity_entry(activity_message)

        return self.refresh_dashboard()

    def log_task_created(self, task_name: str) -> None:
        """Log task creation activity."""
        self.add_activity_entry(f"Task created: {task_name}")

    def log_plan_generated(self, plan_name: str) -> None:
        """Log plan generation activity."""
        self.add_activity_entry(f"Plan generated: {plan_name}")

    def log_task_completed(self, task_name: str) -> None:
        """Log task completion activity."""
        self.add_activity_entry(f"Task completed: {task_name}")

    def log_system_event(self, event: str) -> None:
        """Log system event."""
        self.add_activity_entry(event)
