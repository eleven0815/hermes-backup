# Multi-Repo Project Governance Notes

## Repo Layout Patterns

### Pattern A: Multi-Repo (Independent Git Repos)
```
project-root/
  module-a/.git/
  module-b/.git/
  module-c/.git/
  scripts/
  .githooks/
```

- **Hook strategy:** Copy `pre-commit` into each `module-*/.git/hooks/`
- **Why not `core.hooksPath`:** `git config core.hooksPath` only affects ONE repo. Each submodule is its own repo.
- **Auto-add monitor:** Discover repos by scanning for `.git` directories; iterate independently.

### Pattern B: Monorepo (Single Git Repo)
```
project-root/.git/
  module-a/
  module-b/
  module-c/
```

- **Hook strategy:** `git config core.hooksPath .githooks` at root
- **Auto-add monitor:** Single `git status` call at root is sufficient

## File Watching: Polling vs Native

Native file watchers (`watchdog` Python package, `fswatch` CLI) provide instant notifications but are often unavailable in production dev environments.

| Approach | Latency | Dependency | Robustness |
|----------|---------|-----------|------------|
| `watchdog` (inotify/fsevents) | Instant | `pip install watchdog` | Broken in some containers/VMs |
| `fswatch` | Instant | `brew install fswatch` | macOS only, often missing |
| `git status` polling (5s) | 0–5s | None (git only) | Universal, always works |

**Recommendation:** Use polling for setup scripts. It is dependency-free and works on every platform. The 5-second delay is acceptable for development workflows.

## Path Resolution in Multi-Repo Hooks

When `check-structure.py` is invoked from a pre-commit hook inside `module-a/.git/hooks/pre-commit`, the working directory is `module-a/`, not `project-root/`.

**Critical fix:** The `--git-staged` mode must resolve file paths relative to `os.getcwd()` rather than a hardcoded `PROJECT_ROOT`:

```python
# BAD — breaks in multi-repo hooks
files = [os.path.join(ROOT_DIR, f) for f in output.strip().split("\n") if f]

# GOOD — works wherever the hook runs
cwd = os.getcwd()
files = [os.path.join(cwd, f) for f in output.strip().split("\n") if f]
```

## Pre-Commit Hook Path Derivation

From `.git/hooks/pre-commit`, derive the project root:

```bash
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"      # module/.git/hooks
MODULE_DIR="$(cd "$HOOK_DIR/../.." && pwd)"    # module/
PROJECT_ROOT="$(cd "$MODULE_DIR/.." && pwd)"   # project-root/
```

This is more reliable than hardcoding paths or relying on `$PWD`.

## What to Check vs What to Ignore

| Check | Rationale |
|-------|-----------|
| Only `--diff-filter=A` (new files) | Legacy code may predate new rules; don't block maintenance commits |
| Package prefix by submodule type | `service` uses different prefix than `api`/`app`/`infrastructure` |
| Forbidden imports by layer | `service` must not reference MyBatis, Redis, MQ directly |
| Forbidden annotations by layer | `api` must not contain `@Controller`/`@Service`/`@Mapper` |

| Ignore | Rationale |
|--------|-----------|
| Non-Java files | Structure rules only apply to Java source |
| Modified (not new) Java files | Don't retroactively enforce on legacy code |
| Deleted files | Nothing to validate |
