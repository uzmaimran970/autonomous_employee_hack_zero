#!/usr/bin/env bash
# Pre-commit hook: Reject commits containing credentials or sensitive files.
# Install: cp scripts/pre-commit-credential-check.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -euo pipefail

RED='\033[0;31m'
NC='\033[0m'
BLOCKED=0

# Check for sensitive file extensions
for ext in .pem .key .env .p12 .pfx .jks; do
    FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "${ext}$" || true)
    if [ -n "$FILES" ]; then
        echo -e "${RED}BLOCKED: Sensitive file staged: ${FILES}${NC}"
        BLOCKED=1
    fi
done

# Check staged file contents for credential patterns
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|md|txt|json|yaml|yml|toml|cfg|ini|sh)$' || true)

for FILE in $STAGED_FILES; do
    if [ -f "$FILE" ]; then
        # AWS access keys
        if grep -qP 'AKIA[0-9A-Z]{16}' "$FILE" 2>/dev/null; then
            echo -e "${RED}BLOCKED: AWS key pattern in ${FILE}${NC}"
            BLOCKED=1
        fi
        # Generic API keys/tokens
        if grep -qiP '(?:api[_-]?key|api[_-]?token)\s*[:=]\s*["\x27]?[\w\-]{20,}' "$FILE" 2>/dev/null; then
            echo -e "${RED}BLOCKED: API key/token pattern in ${FILE}${NC}"
            BLOCKED=1
        fi
        # PEM private keys
        if grep -q 'BEGIN.*PRIVATE KEY' "$FILE" 2>/dev/null; then
            echo -e "${RED}BLOCKED: Private key in ${FILE}${NC}"
            BLOCKED=1
        fi
        # Password fields
        if grep -qiP '(?:password|passwd|pwd)\s*[:=]\s*["\x27]?[^\s"'\'']{8,}' "$FILE" 2>/dev/null; then
            echo -e "${RED}BLOCKED: Password pattern in ${FILE}${NC}"
            BLOCKED=1
        fi
    fi
done

if [ "$BLOCKED" -eq 1 ]; then
    echo -e "${RED}Commit rejected: credential patterns detected. Remove or use .gitignore.${NC}"
    exit 1
fi

exit 0
