#!/bin/bash
# Hermes Daily Backup Script
set -e

cd ~/.hermes

# Stage all changes except ignored files
git add -A

# Only commit if there are changes
if git diff --cached --quiet; then
    echo "📦 No changes to backup."
    exit 0
fi

DATE=$(date +%Y%m%d_%H%M)
git commit -m "backup: ${DATE}"

# Push if remote is configured
if git remote get-url origin >/dev/null 2>&1; then
    git push origin main
    echo "✅ Backup committed and pushed to GitHub: ${DATE}"
else
    echo "⚠️ Backup committed locally: ${DATE}"
    echo "   Remote not configured. To push to GitHub:"
    echo "   git remote add origin <your-private-repo-url>"
    echo "   git branch -M main"
    echo "   git push -u origin main"
fi
