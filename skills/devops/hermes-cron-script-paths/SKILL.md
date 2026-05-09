---
name: hermes-cron-script-paths
description: Hermes cron job script path resolution rules and common pitfalls.
triggers:
  - hermes cron script
  - cron script path
  - script not found cron
---

# Hermes Cron Script Path Resolution

## Core Rule

When attaching a script to a Hermes cron job via `--script`, the path is **always resolved relative to `~/.hermes/scripts/`**.

| What you type | Resolved path | Result |
|---|---|---|
| `dispatch.sh` | `~/.hermes/scripts/dispatch.sh` | ✅ Correct |
| `scripts/dispatch.sh` | `~/.hermes/scripts/scripts/dispatch.sh` | ❌ Double `scripts/` — file not found |
| `/Users/foo/.hermes/scripts/dispatch.sh` | (rejected by CLI) | ❌ Absolute paths are blocked |
| `~/hermes/scripts/dispatch.sh` | (rejected by CLI) | ❌ Home-relative paths are blocked |

## Error Signature

If you see this in cron output or logs:

```
Script not found: /Users/<user>/.hermes/scripts/scripts/dispatch.sh
```

The fix is to strip the leading `scripts/` segment from the configured path.

## How to Fix

```bash
# Check current script path
hermes cron list

# Edit to use bare filename only
hermes cron edit <job-id> --script "dispatch.sh"

# Verify
hermes cron list
```

## Where Scripts Must Live

All cron scripts must be placed directly in:

```
~/.hermes/scripts/
```

No subdirectories are supported for resolution. If you need organization, use descriptive filenames (e.g., `kanban-dispatch.sh`, `weekly-curator.py`).

## Creating a New Cron Job with a Script

```bash
# 1. Place the script in the correct directory
mv my-script.sh ~/.hermes/scripts/

# 2. Create the cron job referencing only the filename
hermes cron create \
  --name "my-job" \
  --schedule "0 * * * *" \
  --script "my-script.sh" \
  --prompt "Process output"
```

## Proactive Audit

If one job has the double-directory bug, check all cron jobs — they were likely created with the same misunderstanding:

```bash
grep '"script"' ~/.hermes/cron/jobs.json
```

Any value starting with `scripts/` should be corrected to the bare filename.
