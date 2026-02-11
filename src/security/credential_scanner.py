"""
Credential Scanner for Silver Tier Foundation.

Scans vault files for credential patterns (API keys, tokens,
passwords, PEM keys) and flags them for review.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


# Compiled regex patterns for credential detection
CREDENTIAL_PATTERNS = {
    'aws_access_key': re.compile(
        r'(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}', re.IGNORECASE),
    'api_token': re.compile(
        r'(?:api[_-]?key|api[_-]?token|apikey)\s*[:=]\s*["\']?[\w\-]{20,}',
        re.IGNORECASE),
    'pem_key': re.compile(
        r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----'),
    'password_field': re.compile(
        r'(?:password|passwd|pwd)\s*[:=]\s*["\']?[^\s"\']{8,}',
        re.IGNORECASE),
    'generic_secret': re.compile(
        r'(?:secret|token|bearer)\s*[:=]\s*["\']?[\w\-/.]{20,}',
        re.IGNORECASE),
    'connection_string': re.compile(
        r'(?:mongodb|postgres|mysql|redis)://\S+:\S+@', re.IGNORECASE),
}


class CredentialScanner:
    """
    Scans files for credential patterns.

    Uses 6 compiled regex patterns to detect:
    - AWS access keys
    - API tokens/keys
    - PEM private keys
    - Password fields
    - Generic secrets/tokens
    - Connection strings with embedded credentials
    """

    def __init__(self):
        """Initialize CredentialScanner."""
        self.patterns = CREDENTIAL_PATTERNS

    def scan_file(self, file_path: Path) -> List[Dict]:
        """
        Scan a single file for credential patterns.

        Args:
            file_path: Path to the file to scan.

        Returns:
            List of finding dicts with 'pattern', 'line', 'match' keys.
        """
        findings = []

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Cannot read file for scanning: {file_path}: {e}")
            return findings

        for line_num, line in enumerate(content.split('\n'), 1):
            for pattern_name, pattern in self.patterns.items():
                matches = pattern.findall(line)
                if matches:
                    for match in matches:
                        # Partially mask the match for safe logging
                        masked = self._mask_value(str(match))
                        findings.append({
                            'pattern': pattern_name,
                            'line': line_num,
                            'match': masked,
                            'file': str(file_path),
                        })

        return findings

    def scan_vault(self, vault_path: Path) -> List[Dict]:
        """
        Scan all files in the vault for credential patterns.

        Args:
            vault_path: Path to the vault root.

        Returns:
            List of all finding dicts across all files.
        """
        all_findings = []
        vault_path = Path(vault_path)

        if not vault_path.exists():
            logger.error(f"Vault path not found: {vault_path}")
            return all_findings

        # Scan all markdown files in vault subfolders
        for folder in ['Needs_Action', 'In_Progress', 'Done', 'Plans']:
            folder_path = vault_path / folder
            if not folder_path.exists():
                continue

            for file_path in folder_path.glob('*.md'):
                findings = self.scan_file(file_path)
                all_findings.extend(findings)

        return all_findings

    def _mask_value(self, value: str) -> str:
        """
        Partially mask a credential value for safe display.

        Shows first 4 and last 2 characters, masks the rest.

        Args:
            value: The credential string.

        Returns:
            Partially masked string.
        """
        if len(value) <= 8:
            return value[:2] + '*' * (len(value) - 2)
        return value[:4] + '*' * (len(value) - 6) + value[-2:]
