#!/bin/bash
# Security Audit Script for Bronze Tier Foundation
# Verifies no credentials are stored in the vault

set -e

VAULT_PATH="${1:-./autonomous_employee}"

echo "🔒 Security Audit for Bronze Tier Foundation"
echo "============================================"
echo ""
echo "Vault path: $VAULT_PATH"
echo ""

# Check if vault exists
if [ ! -d "$VAULT_PATH" ]; then
    echo "❌ Vault directory not found: $VAULT_PATH"
    exit 1
fi

ISSUES_FOUND=0

# Check 1: Search for potential credentials in vault
echo "Checking for potential credentials in vault..."
if grep -rE "(api[_-]?key|password|secret|token|credential)[[:space:]]*[:=]" "$VAULT_PATH" --include="*.md" 2>/dev/null; then
    echo "⚠️  WARNING: Potential credentials found in vault files!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo "✅ No credentials detected in vault files"
fi

# Check 2: Verify .env is in .gitignore
echo ""
echo "Checking .gitignore for .env..."
if [ -f ".gitignore" ]; then
    if grep -q "^\.env$\|^\.env\b" .gitignore; then
        echo "✅ .env is properly listed in .gitignore"
    else
        echo "⚠️  WARNING: .env is NOT in .gitignore!"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
else
    echo "⚠️  WARNING: .gitignore file not found!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Check 3: Verify .env exists but is not committed
echo ""
echo "Checking .env file status..."
if [ -f ".env" ]; then
    if git ls-files --error-unmatch .env 2>/dev/null; then
        echo "❌ CRITICAL: .env is tracked by git!"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo "✅ .env exists and is not tracked by git"
    fi
else
    echo "ℹ️  .env file not found (optional)"
fi

# Check 4: Verify token.json is not committed
echo ""
echo "Checking for OAuth tokens..."
if [ -f "token.json" ]; then
    if git ls-files --error-unmatch token.json 2>/dev/null; then
        echo "❌ CRITICAL: token.json is tracked by git!"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo "✅ token.json exists but is not tracked by git"
    fi
else
    echo "✅ No token.json file found"
fi

# Check 5: Verify credentials.json is not committed
if [ -f "credentials.json" ]; then
    if git ls-files --error-unmatch credentials.json 2>/dev/null; then
        echo "❌ CRITICAL: credentials.json is tracked by git!"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo "✅ credentials.json exists but is not tracked by git"
    fi
fi

# Summary
echo ""
echo "============================================"
if [ $ISSUES_FOUND -eq 0 ]; then
    echo "✅ Security audit PASSED - No issues found"
    exit 0
else
    echo "❌ Security audit FAILED - $ISSUES_FOUND issue(s) found"
    echo ""
    echo "Please fix the issues above before proceeding."
    exit 1
fi
