"""
Vault Initializer for Bronze Tier Foundation.

Creates the Obsidian vault structure with required folders and files.
This is typically run once during initial setup.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from utils.vault_manager import VaultManager

logger = logging.getLogger(__name__)


# Dashboard template content
DASHBOARD_TEMPLATE = """# Dashboard

**Last Updated**: {timestamp}

## Recent Activity

- No tasks yet

## Statistics

- **Pending Tasks**: 0
- **Completed Tasks**: 0
- **Plans Generated**: 0

## Watcher Status

- **File Watcher**: Not started
- **Gmail Watcher**: Not configured
"""

# Company Handbook template content
COMPANY_HANDBOOK_TEMPLATE = """# Company Handbook

## AI Behavior Rules

1. **Politeness**: All generated plans must use professional language
2. **Clarity**: Steps must be understandable without technical knowledge
3. **Safety**: Never include credentials or sensitive data in output
4. **Scope**: Generate plans only - do not execute actions
5. **Brevity**: Keep steps concise and actionable

## Task Processing Guidelines

- Each task gets exactly one plan file
- Plans must have at least 3 actionable steps
- Steps must be checkbox-formatted for tracking
- Reference the original task in the plan header

## Response Formatting

- Use bullet points for lists
- Use headers to organize content
- Keep paragraphs short (3-4 sentences max)

## Bronze Tier Constraints

- Plan generation only - no automatic execution
- Manual task movement from /Needs_Action to /Done
- No external API calls beyond Gmail (if configured)
- Single user, single machine operation
"""


def create_folders(vault_path: Path) -> bool:
    """
    Create the required folder structure for the vault.

    Creates:
    - /Needs_Action: For incoming tasks
    - /In_Progress: For tasks currently being processed
    - /Done: For completed tasks
    - /Plans: For generated action plans
    - /Rollback_Archive: For rollback snapshots (Gold Tier)

    Args:
        vault_path: Path to the vault root directory.

    Returns:
        True if successful, False otherwise.
    """
    folders = ['Needs_Action', 'In_Progress', 'Done', 'Plans', 'Rollback_Archive', 'Learning_Data']

    try:
        # Create vault root if it doesn't exist
        vault_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created vault root: {vault_path}")

        # Create subfolders
        for folder in folders:
            folder_path = vault_path / folder
            folder_path.mkdir(exist_ok=True)
            logger.info(f"Created folder: {folder_path}")

        return True
    except Exception as e:
        logger.error(f"Error creating folders: {e}")
        return False


def write_dashboard(vault_path: Path) -> bool:
    """
    Create the Dashboard.md file in the vault root.

    Args:
        vault_path: Path to the vault root directory.

    Returns:
        True if successful, False otherwise.
    """
    dashboard_path = vault_path / 'Dashboard.md'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        content = DASHBOARD_TEMPLATE.format(timestamp=timestamp)
        dashboard_path.write_text(content, encoding='utf-8')
        logger.info(f"Created Dashboard.md: {dashboard_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating Dashboard.md: {e}")
        return False


def write_handbook(vault_path: Path) -> bool:
    """
    Create the Company_Handbook.md file in the vault root.

    Args:
        vault_path: Path to the vault root directory.

    Returns:
        True if successful, False otherwise.
    """
    handbook_path = vault_path / 'Company_Handbook.md'

    try:
        handbook_path.write_text(COMPANY_HANDBOOK_TEMPLATE, encoding='utf-8')
        logger.info(f"Created Company_Handbook.md: {handbook_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating Company_Handbook.md: {e}")
        return False


def create_hash_registry(vault_path: Path) -> bool:
    """
    Create the hidden .task_hashes file for deduplication.

    Args:
        vault_path: Path to the vault root directory.

    Returns:
        True if successful, False otherwise.
    """
    hash_file = vault_path / '.task_hashes'

    try:
        if not hash_file.exists():
            hash_file.touch()
            logger.info(f"Created hash registry: {hash_file}")
        return True
    except Exception as e:
        logger.error(f"Error creating hash registry: {e}")
        return False


def init_vault(vault_path: Optional[Path] = None) -> bool:
    """
    Initialize a complete vault structure.

    This is the main entry point for vault initialization.
    Creates all required folders and files.

    Args:
        vault_path: Path to create the vault. If None, uses current
                   directory with 'autonomous_employee' subfolder.

    Returns:
        True if successful, False otherwise.
    """
    if vault_path is None:
        vault_path = Path.cwd() / 'autonomous_employee'

    vault_path = Path(vault_path)

    logger.info(f"Initializing vault at: {vault_path}")

    # Step 1: Create folder structure
    if not create_folders(vault_path):
        logger.error("Failed to create folder structure")
        return False

    # Step 2: Create Dashboard.md
    if not write_dashboard(vault_path):
        logger.error("Failed to create Dashboard.md")
        return False

    # Step 3: Create Company_Handbook.md
    if not write_handbook(vault_path):
        logger.error("Failed to create Company_Handbook.md")
        return False

    # Step 4: Create hash registry
    if not create_hash_registry(vault_path):
        logger.error("Failed to create hash registry")
        return False

    # Step 5: Validate the structure
    manager = VaultManager(vault_path)
    is_valid, missing = manager.validate_structure()

    if is_valid:
        logger.info("Vault initialization complete!")
        print(f"\n✅ Vault initialized successfully at: {vault_path}")
        print("\nCreated structure:")
        print("  autonomous_employee/")
        print("  ├── Needs_Action/")
        print("  ├── In_Progress/")
        print("  ├── Done/")
        print("  ├── Plans/")
        print("  ├── Rollback_Archive/")
        print("  ├── Dashboard.md")
        print("  ├── Company_Handbook.md")
        print("  └── .task_hashes")
        return True
    else:
        logger.error(f"Vault validation failed. Missing: {missing}")
        return False


if __name__ == "__main__":
    # Allow running directly for testing
    import sys

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = None

    success = init_vault(path)
    sys.exit(0 if success else 1)
