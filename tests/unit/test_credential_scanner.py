"""
Unit tests for CredentialScanner.
"""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from security.credential_scanner import CredentialScanner, CREDENTIAL_PATTERNS


class TestCredentialScanner:
    """Tests for CredentialScanner class."""

    def test_init(self):
        """Test CredentialScanner initialization."""
        scanner = CredentialScanner()
        assert scanner.patterns is not None
        assert len(scanner.patterns) == 6

    def test_has_all_six_patterns(self):
        """Test that all 6 expected patterns are present."""
        expected = {
            'aws_access_key', 'api_token', 'pem_key',
            'password_field', 'generic_secret', 'connection_string',
        }
        assert set(CREDENTIAL_PATTERNS.keys()) == expected

    # --- Pattern-specific detection tests ---

    def test_detect_aws_access_key(self, tmp_path):
        """Test detection of AWS access key pattern."""
        scanner = CredentialScanner()
        file_path = tmp_path / "aws.md"
        file_path.write_text("config:\n  aws_key: AKIAIOSFODNN7EXAMPLE\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'aws_access_key' for f in findings)

    def test_detect_api_token(self, tmp_path):
        """Test detection of API token pattern."""
        scanner = CredentialScanner()
        file_path = tmp_path / "api.md"
        file_path.write_text("api_key = abc123def456ghi789jkl012mno345\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'api_token' for f in findings)

    def test_detect_api_token_with_colon(self, tmp_path):
        """Test detection of API token with colon separator."""
        scanner = CredentialScanner()
        file_path = tmp_path / "api2.md"
        file_path.write_text("api-token: abcdefghijklmnopqrstuvwxyz1234\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'api_token' for f in findings)

    def test_detect_pem_key(self, tmp_path):
        """Test detection of PEM private key pattern."""
        scanner = CredentialScanner()
        file_path = tmp_path / "key.md"
        file_path.write_text(
            "Here is a key:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/yGaF...\n"
            "-----END RSA PRIVATE KEY-----\n"
        )

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'pem_key' for f in findings)

    def test_detect_pem_key_ec(self, tmp_path):
        """Test detection of EC private key pattern."""
        scanner = CredentialScanner()
        file_path = tmp_path / "eckey.md"
        file_path.write_text("-----BEGIN EC PRIVATE KEY-----\nfakedata\n-----END EC PRIVATE KEY-----\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'pem_key' for f in findings)

    def test_detect_password_field(self, tmp_path):
        """Test detection of password field pattern."""
        scanner = CredentialScanner()
        file_path = tmp_path / "passwd.md"
        file_path.write_text("password = SuperSecret123!\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'password_field' for f in findings)

    def test_detect_password_with_colon(self, tmp_path):
        """Test detection of password with colon separator."""
        scanner = CredentialScanner()
        file_path = tmp_path / "passwd2.md"
        file_path.write_text("passwd: MyLongPassword99\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'password_field' for f in findings)

    def test_detect_generic_secret(self, tmp_path):
        """Test detection of generic secret/token pattern."""
        scanner = CredentialScanner()
        file_path = tmp_path / "secret.md"
        file_path.write_text("secret = abcdefghijklmnopqrstuvwxyz1234567890\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'generic_secret' for f in findings)

    def test_detect_bearer_token(self, tmp_path):
        """Test detection of bearer token pattern."""
        scanner = CredentialScanner()
        file_path = tmp_path / "bearer.md"
        file_path.write_text("bearer = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'generic_secret' for f in findings)

    def test_detect_connection_string_postgres(self, tmp_path):
        """Test detection of PostgreSQL connection string."""
        scanner = CredentialScanner()
        file_path = tmp_path / "connstr.md"
        file_path.write_text("db_url = postgres://admin:password123@db.example.com:5432/mydb\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'connection_string' for f in findings)

    def test_detect_connection_string_mongodb(self, tmp_path):
        """Test detection of MongoDB connection string."""
        scanner = CredentialScanner()
        file_path = tmp_path / "mongo.md"
        file_path.write_text("MONGO_URI=mongodb://user:pass@cluster.example.com/db\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'connection_string' for f in findings)

    def test_detect_connection_string_mysql(self, tmp_path):
        """Test detection of MySQL connection string."""
        scanner = CredentialScanner()
        file_path = tmp_path / "mysql.md"
        file_path.write_text("url = mysql://root:secret@localhost:3306/app\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'connection_string' for f in findings)

    def test_detect_connection_string_redis(self, tmp_path):
        """Test detection of Redis connection string."""
        scanner = CredentialScanner()
        file_path = tmp_path / "redis.md"
        file_path.write_text("REDIS_URL=redis://default:mypassword@redis.example.com:6379\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'connection_string' for f in findings)

    # --- scan_file behavior tests ---

    def test_scan_file_clean_file(self, tmp_path):
        """Test that a clean file with no credentials returns no findings."""
        scanner = CredentialScanner()
        file_path = tmp_path / "clean.md"
        file_path.write_text(
            "# Meeting Notes\n\n"
            "- Discussed project timeline\n"
            "- Agreed on Sprint 5 goals\n"
            "- Reviewed design documents\n"
        )

        findings = scanner.scan_file(file_path)
        assert len(findings) == 0

    def test_scan_file_reports_line_numbers(self, tmp_path):
        """Test that findings include correct line numbers."""
        scanner = CredentialScanner()
        file_path = tmp_path / "lines.md"
        file_path.write_text(
            "Line one is clean\n"
            "Line two is clean\n"
            "password = VerySecretPassword123\n"
            "Line four is clean\n"
        )

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert findings[0]['line'] == 3

    def test_scan_file_multiple_patterns_in_one_file(self, tmp_path):
        """Test that multiple different credential patterns are detected."""
        scanner = CredentialScanner()
        file_path = tmp_path / "multi.md"
        file_path.write_text(
            "aws_key: AKIAIOSFODNN7EXAMPLE\n"
            "password = SuperSecret123!\n"
            "postgres://admin:pass@host:5432/db\n"
        )

        findings = scanner.scan_file(file_path)
        patterns_found = {f['pattern'] for f in findings}
        assert 'aws_access_key' in patterns_found
        assert 'password_field' in patterns_found
        assert 'connection_string' in patterns_found

    def test_scan_file_nonexistent_file(self, tmp_path):
        """Test scanning a file that does not exist."""
        scanner = CredentialScanner()
        file_path = tmp_path / "nonexistent.md"

        findings = scanner.scan_file(file_path)
        assert findings == []

    def test_scan_file_includes_file_path(self, tmp_path):
        """Test that findings include the file path."""
        scanner = CredentialScanner()
        file_path = tmp_path / "filepath.md"
        file_path.write_text("password = LongEnoughPassword1\n")

        findings = scanner.scan_file(file_path)
        assert len(findings) >= 1
        assert findings[0]['file'] == str(file_path)

    # --- Partial masking tests ---

    def test_mask_value_short_string(self):
        """Test masking of short credential values (<=8 chars)."""
        scanner = CredentialScanner()
        masked = scanner._mask_value("abcdefgh")
        assert masked.startswith("ab")
        assert '*' in masked
        assert len(masked) == 8

    def test_mask_value_long_string(self):
        """Test masking of long credential values (>8 chars)."""
        scanner = CredentialScanner()
        value = "AKIAIOSFODNN7EXAMPLE"
        masked = scanner._mask_value(value)
        # Shows first 4 and last 2 characters
        assert masked[:4] == "AKIA"
        assert masked[-2:] == "LE"
        assert '*' in masked
        assert len(masked) == len(value)

    def test_mask_value_preserves_length(self):
        """Test that masking preserves original string length."""
        scanner = CredentialScanner()
        for length in [6, 8, 10, 20, 50]:
            value = "a" * length
            masked = scanner._mask_value(value)
            assert len(masked) == length

    # --- scan_vault tests ---

    def test_scan_vault(self, temp_vault):
        """Test scanning the entire vault."""
        scanner = CredentialScanner()

        # Create a file with credentials in Needs_Action
        cred_file = temp_vault / 'Needs_Action' / 'cred-task.md'
        cred_file.write_text("password = MySecretPassword123\n")

        # Create a clean file in Done
        clean_file = temp_vault / 'Done' / 'clean-task.md'
        clean_file.write_text("# Clean Task\n\nNo secrets here.\n")

        findings = scanner.scan_vault(temp_vault)
        assert len(findings) >= 1
        assert any(f['pattern'] == 'password_field' for f in findings)

    def test_scan_vault_empty(self, temp_vault):
        """Test scanning vault with no credential files."""
        scanner = CredentialScanner()
        findings = scanner.scan_vault(temp_vault)
        assert findings == []

    def test_scan_vault_nonexistent_path(self, tmp_path):
        """Test scanning a vault path that does not exist."""
        scanner = CredentialScanner()
        findings = scanner.scan_vault(tmp_path / "nonexistent_vault")
        assert findings == []
