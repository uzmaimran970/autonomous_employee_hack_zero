"""
Gmail Watcher for Bronze Tier Foundation (Optional).

Monitors Gmail for unread important emails and creates tasks.
Requires OAuth2 configuration in .env file.

This watcher is OPTIONAL - the system works with FileWatcher alone.
"""

import logging
import time
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import frontmatter

from watchers.base_watcher import BaseWatcher
from utils.hash_registry import HashRegistry
from utils.vault_manager import VaultManager

logger = logging.getLogger(__name__)

# Gmail API imports (optional dependency)
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logger.warning("Gmail dependencies not installed. Gmail watcher unavailable.")


class GmailWatcher(BaseWatcher):
    """
    Watches Gmail for unread important emails and creates tasks.

    Requires:
    - google-api-python-client
    - google-auth-httplib2
    - google-auth-oauthlib
    - OAuth2 credentials configured in .env
    """

    SOURCE_TYPE = 'gmail'
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self, vault_path: Path,
                 credentials_path: Optional[Path] = None,
                 token_path: Optional[Path] = None,
                 check_interval: int = 300):
        """
        Initialize the GmailWatcher.

        Args:
            vault_path: Path to the Obsidian vault root.
            credentials_path: Path to OAuth2 credentials.json file.
            token_path: Path to store/load the token.json file.
            check_interval: Seconds between email checks (default: 5 minutes).
        """
        super().__init__(vault_path)

        if not GMAIL_AVAILABLE:
            raise ImportError(
                "Gmail dependencies not installed. "
                "Install with: pip install google-api-python-client "
                "google-auth-httplib2 google-auth-oauthlib"
            )

        self.credentials_path = credentials_path
        self.token_path = token_path or (vault_path.parent / 'token.json')
        self.check_interval = check_interval
        self.vault_manager = VaultManager(vault_path)
        self.hash_registry = HashRegistry(vault_path)
        self.service = None
        self._processed_ids: set = set()

    def _authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.

        Returns:
            True if authentication successful, False otherwise.
        """
        creds = None

        # Load existing token
        if self.token_path and self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path), self.SCOPES
                )
            except Exception as e:
                logger.error(f"Error loading token: {e}")

        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    creds = None

            if not creds:
                if not self.credentials_path or not self.credentials_path.exists():
                    logger.error("No credentials file found")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for next time
            if self.token_path:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())

        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail authentication successful")
            return True
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            return False

    def watch(self) -> None:
        """
        Start watching Gmail for new emails.

        Polls Gmail at configured interval. Blocks until stop() is called.
        """
        if not self._authenticate():
            raise RuntimeError("Gmail authentication failed")

        logger.info("Starting Gmail watcher")
        print(f"📧 Watching Gmail for new emails")
        print(f"📂 Tasks will be saved to: {self.needs_action_path}")
        print(f"⏱️  Check interval: {self.check_interval} seconds")
        print("Press Ctrl+C to stop...")

        self.is_running = True

        try:
            while self.is_running:
                self._check_emails()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Gmail watcher interrupted by user")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop watching Gmail."""
        self.is_running = False
        logger.info("Gmail watcher stopped")

    def _check_emails(self) -> None:
        """Check for new unread important emails."""
        try:
            # Query for unread important emails
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread is:important',
                maxResults=10
            ).execute()

            messages = results.get('messages', [])
            logger.debug(f"Found {len(messages)} unread important emails")

            for msg in messages:
                msg_id = msg['id']
                if msg_id not in self._processed_ids:
                    self._process_email(msg_id)
                    self._processed_ids.add(msg_id)

        except Exception as e:
            logger.error(f"Error checking emails: {e}")

    def _process_email(self, msg_id: str) -> None:
        """
        Process a single email and create a task.

        Args:
            msg_id: Gmail message ID.
        """
        try:
            # Get full message
            message = self.service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()

            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}

            subject = header_dict.get('subject', 'No Subject')
            from_addr = header_dict.get('from', 'Unknown')
            date = header_dict.get('date', '')

            # Extract body
            body = self._extract_body(message)

            # Check for duplicate
            content_hash = self.hash_registry.compute_hash(f"{msg_id}{subject}")
            if self.hash_registry.has_hash(content_hash):
                logger.debug(f"Duplicate email, skipping: {subject}")
                return

            # Create task
            content = f"""**From**: {from_addr}
**Date**: {date}

---

{body}
"""

            task_path = self.create_task(
                title=subject,
                content=content,
                source=self.SOURCE_TYPE,
                original_ref=msg_id
            )

            if task_path:
                self.hash_registry.add_hash(content_hash)
                print(f"✅ Created task from email: {subject[:50]}...")

        except Exception as e:
            logger.error(f"Error processing email {msg_id}: {e}")

    def _extract_body(self, message: Dict[str, Any]) -> str:
        """
        Extract email body from message.

        Args:
            message: Gmail message object.

        Returns:
            Email body text.
        """
        payload = message.get('payload', {})

        # Check for plain text body
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8', errors='ignore')

        # Check parts for text/plain
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                if part.get('body', {}).get('data'):
                    return base64.urlsafe_b64decode(
                        part['body']['data']
                    ).decode('utf-8', errors='ignore')

        return "(Email body could not be extracted)"

    def create_task(self, title: str, content: str,
                    source: str, original_ref: str,
                    file_type: str = 'email') -> Optional[Path]:
        """
        Create a task file in the Needs_Action folder.

        Args:
            title: Task title (email subject)
            content: Task content (email body)
            source: Source type ('gmail')
            original_ref: Gmail message ID
            file_type: File type category (always 'email' for Gmail)

        Returns:
            Path to created task file, or None if failed.
        """
        filename = self.generate_task_filename(title)
        body, metadata = self.format_task_content(
            title, content, source, original_ref, file_type='email')

        task_path = self.needs_action_path / filename

        try:
            post = frontmatter.Post(body, **metadata)
            with open(task_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))

            logger.info(f"Created task from email: {task_path}")
            return task_path
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None
