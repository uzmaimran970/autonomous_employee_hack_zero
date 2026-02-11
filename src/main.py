#!/usr/bin/env python3
"""
Main entry point for Gold Tier Foundation.

Provides CLI interface for:
- Initializing the vault
- Running the file watcher
- Processing tasks and generating plans
- Running the continuous loop with auto-move, classification, rollback, SLA, notifications
- Security scanning
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from utils.config import load_config, get_config
from utils.vault_initializer import init_vault
from utils.vault_manager import VaultManager
from utils.dashboard_updater import DashboardUpdater
from utils.operations_logger import OperationsLogger
from watchers.file_watcher import FileWatcher
from processors.task_processor import TaskProcessor
from orchestrator.task_mover import TaskMover
from orchestrator.rollback_manager import RollbackManager
from orchestrator.sla_tracker import SLATracker
from notifications.notifier import NoOpNotifier
from notifications.webhook_notifier import WebhookNotifier
from security.credential_scanner import CredentialScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def cmd_init_vault(args):
    """Initialize the vault structure."""
    vault_path = Path(args.path) if args.path else None
    success = init_vault(vault_path)
    return 0 if success else 1


def cmd_watch(args):
    """Start the file watcher."""
    config = get_config()
    vault_path = Path(args.vault) if args.vault else config['vault_path']
    watch_dir = Path(args.dir) if args.dir else config['watch_dir']

    # Validate paths
    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        print("   Run 'python -m src.main --init-vault' first")
        return 1

    if not watch_dir.exists():
        print(f"❌ Watch directory not found: {watch_dir}")
        print(f"   Create it or specify a different directory with --dir")
        return 1

    watcher = FileWatcher(vault_path, watch_dir)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        watcher.watch()
    except Exception as e:
        logger.error(f"Watcher error: {e}")
        return 1

    return 0


def cmd_process(args):
    """Process pending tasks and generate plans."""
    config = get_config()
    vault_path = Path(args.vault) if args.vault else config['vault_path']

    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        return 1

    processor = TaskProcessor(vault_path)
    plans_generated = processor.process_all_pending()

    print(f"\n📋 Generated {plans_generated} new plan(s)")
    return 0


def cmd_loop(args):
    """
    Run the continuous processing loop (Ralph Wiggum loop).

    Combines watching and processing in a single loop.
    """
    global shutdown_requested

    config = get_config()
    vault_path = Path(args.vault) if args.vault else config['vault_path']
    watch_dir = Path(args.dir) if args.dir else config['watch_dir']
    interval = args.interval or config['check_interval_seconds']

    # Validate paths
    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        print("   Run 'python -m src.main --init-vault' first")
        return 1

    if not watch_dir.exists():
        print(f"❌ Watch directory not found: {watch_dir}")
        return 1

    # Initialize components
    ops_logger = OperationsLogger(config['operations_log_path'])
    vault_manager = VaultManager(vault_path)
    watcher = FileWatcher(vault_path, watch_dir)

    # Gold Tier: SLA tracker
    sla_tracker = SLATracker(config=config, ops_logger=ops_logger)

    # Gold Tier: Notifier
    notification_channel = config.get('notification_channel', '')
    notification_endpoint = config.get('notification_endpoint', '')
    if notification_channel == 'webhook' and notification_endpoint:
        notifier = WebhookNotifier(notification_endpoint, ops_logger=ops_logger)
    else:
        notifier = NoOpNotifier()

    processor = TaskProcessor(
        vault_path, ops_logger=ops_logger,
        notifier=notifier, sla_tracker=sla_tracker
    )
    task_mover = TaskMover(vault_manager, ops_logger)
    credential_scanner = CredentialScanner() if config.get('credential_scan_enabled', True) else None
    rollback_manager = RollbackManager(
        vault_path, ops_logger=ops_logger,
        retention_days=config.get('rollback_retention_days', 7)
    )
    dashboard = DashboardUpdater(vault_path, ops_logger=ops_logger)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    in_progress_count = len(vault_manager.get_in_progress_tasks())
    print("\n🤖 Starting Autonomous Employee (Gold Tier)")
    print(f"   Vault: {vault_path}")
    print(f"   Watch: {watch_dir}")
    print(f"   Interval: {interval}s")
    print(f"   In-Progress: {in_progress_count} task(s)")
    print("   Press Ctrl+C to stop\n")

    # Start watcher in non-blocking mode
    try:
        watcher.start_watching()
    except Exception as e:
        logger.error(f"Failed to start watcher: {e}")
        return 1

    loop_count = 0
    try:
        while not shutdown_requested:
            loop_count += 1
            logger.debug(f"Loop iteration {loop_count}")

            # Credential scan before processing
            if credential_scanner:
                findings = credential_scanner.scan_vault(vault_path)
                for finding in findings:
                    logger.warning(
                        f"Credential detected: {finding['pattern']} "
                        f"in {finding['file']} line {finding['line']}"
                    )
                    ops_logger.log(
                        op='credential_flagged',
                        file=Path(finding['file']).name,
                        src=Path(finding['file']).parent.name,
                        outcome='flagged',
                        detail=f"pattern:{finding['pattern']} line:{finding['line']}"
                    )

            # Purge expired rollback snapshots
            rollback_manager.purge_expired()

            # Auto-move tasks based on status
            moved = task_mover.check_and_move_tasks()
            if moved > 0:
                print(f"🔄 Moved {moved} task(s)")

            # Process any pending tasks
            plans_generated = processor.process_all_pending()
            if plans_generated > 0:
                print(f"📋 Generated {plans_generated} new plan(s)")

            # Health-check heartbeat
            try:
                _ = vault_manager.validate_structure()
                _ = processor.read_pending_tasks()
            except Exception as hb_err:
                logger.error(f"Heartbeat failure: {hb_err}")
                ops_logger.log(
                    op='heartbeat_fail',
                    file='system',
                    src='cmd_loop',
                    outcome='failed',
                    detail=str(hb_err)
                )

            # Update dashboard every loop
            dashboard.refresh_dashboard()

            # Wait for next iteration
            time.sleep(interval)

    except Exception as e:
        logger.error(f"Loop error: {e}")
    finally:
        watcher.stop()
        dashboard.refresh_dashboard()
        print("\n👋 Autonomous Employee stopped")

    return 0


def cmd_import(args):
    """Import existing files from a directory as tasks."""
    config = get_config()
    vault_path = Path(args.vault) if args.vault else config['vault_path']
    import_dir = Path(args.dir) if args.dir else config['watch_dir']

    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        return 1

    if not import_dir.exists():
        print(f"❌ Import directory not found: {import_dir}")
        return 1

    watcher = FileWatcher(vault_path, import_dir)
    imported = 0

    print(f"\n📥 Importing files from: {import_dir}")

    for file_path in import_dir.iterdir():
        if file_path.is_file() and not file_path.name.startswith('.'):
            task_path = watcher.create_task_from_file(file_path)
            if task_path:
                imported += 1

    print(f"\n✅ Imported {imported} file(s) as tasks")
    return 0


def cmd_status(args):
    """Show vault status and statistics."""
    config = get_config()
    vault_path = Path(args.vault) if args.vault else config['vault_path']

    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        return 1

    manager = VaultManager(vault_path)
    is_valid, missing = manager.validate_structure()

    print(f"\n📊 Vault Status: {vault_path}")
    print("=" * 50)

    if is_valid:
        print("✅ Structure: Valid")
    else:
        print("❌ Structure: Invalid")
        for item in missing:
            print(f"   Missing: {item}")

    pending = len(manager.get_pending_tasks())
    in_progress = len(manager.get_in_progress_tasks())
    completed = len(manager.get_completed_tasks())
    plans = len(manager.get_plans())

    print(f"\n📈 Statistics:")
    print(f"   Pending Tasks: {pending}")
    print(f"   In-Progress Tasks: {in_progress}")
    print(f"   Completed Tasks: {completed}")
    print(f"   Plans Generated: {plans}")

    return 0


def cmd_scan(args):
    """Run credential scanner on vault."""
    config = get_config()
    vault_path = Path(args.vault) if args.vault else config['vault_path']

    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        return 1

    scanner = CredentialScanner()
    findings = scanner.scan_vault(vault_path)

    if not findings:
        print("\n✅ No credential patterns detected in vault")
        return 0

    print(f"\n⚠️  Found {len(findings)} credential pattern(s):\n")
    for f in findings:
        print(f"  {f['pattern']} in {f['file']} line {f['line']}: {f['match']}")

    return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Silver Tier Foundation - Autonomous Employee",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --init-vault              Initialize vault structure
  python -m src.main --import --dir ./inbox    Import files from directory as tasks
  python -m src.main --watch --dir ./inbox     Watch directory for new files
  python -m src.main --process                 Process pending tasks
  python -m src.main --loop                    Run continuous loop
  python -m src.main --status                  Show vault status
  python -m src.main --scan                    Scan vault for credentials
        """
    )

    # Global options
    parser.add_argument('--vault', type=str, help='Path to Obsidian vault')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    # Commands
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--init-vault', action='store_true',
                       help='Initialize vault structure')
    group.add_argument('--watch', action='store_true',
                       help='Start file watcher')
    group.add_argument('--process', action='store_true',
                       help='Process pending tasks')
    group.add_argument('--loop', action='store_true',
                       help='Run continuous processing loop')
    group.add_argument('--status', action='store_true',
                       help='Show vault status')
    group.add_argument('--scan', action='store_true',
                       help='Scan vault for credential patterns')
    group.add_argument('--import', action='store_true', dest='import_files',
                       help='Import existing files from directory as tasks')

    # Watch options
    parser.add_argument('--dir', type=str,
                        help='Directory to watch (for --watch and --loop)')
    parser.add_argument('--interval', type=int,
                        help='Check interval in seconds (for --loop)')

    # Init options
    parser.add_argument('--path', type=str,
                        help='Vault path (for --init-vault)')

    args = parser.parse_args()

    # Load configuration
    load_config()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Dispatch to command handler
    if args.init_vault:
        return cmd_init_vault(args)
    elif args.watch:
        return cmd_watch(args)
    elif args.process:
        return cmd_process(args)
    elif args.loop:
        return cmd_loop(args)
    elif args.status:
        return cmd_status(args)
    elif args.scan:
        return cmd_scan(args)
    elif args.import_files:
        return cmd_import(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
