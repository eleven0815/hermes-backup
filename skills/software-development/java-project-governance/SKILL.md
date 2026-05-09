---
name: java-project-governance
description: "Set up automated project structure governance for Java layered-architecture projects: pre-commit hooks, package naming validation, layer constraint checks, and multi-repo coordination."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [java, project-governance, pre-commit-hooks, layered-architecture, code-quality, git-hooks, multi-repo]
    related_skills: [requesting-code-review, jac-interface-dev-workflow]
---

# Java Project Governance

Automated enforcement of project structure, package naming, and layered-architecture constraints for Java projects with `api`/`app`/`service`/`infrastructure` modules. Works across multiple independent Git repositories under a common parent directory.

## When to Use

- User asks to enforce package naming conventions across backend modules
- User wants pre-commit hooks that validate architecture layer constraints
- Project has multiple independent Git repos (not a monorepo with single `.git`)
- Need auto `git add` with structure checking, but **never** auto commit/push
- Setting up governance for YonBIP / iuap / Spring-Boot layered projects

## Architecture Target

Standard six-submodule Maven backend:

| Layer | Directory suffix | Package prefix | Responsibility |
|-------|-----------------|----------------|----------------|
| `api` | `-api` | `com.yonyou.oem.{engine}.{app}` | RPC interfaces, DTOs, enums, error codes |
| `app` | `-app` | `com.yonyou.oem.{engine}.{app}` | Controllers only, no business logic |
| `service` | `-service` | `com.yonyou.dcs.{engine}.{app}` | Service interfaces, implementations, plugins, repository **interfaces** |
| `infrastructure` | `-infrastructure` | `com.yonyou.oem.{engine}.{app}` | Repository implementations, POs, external APIs, Redis/MQ |
| `bootstrap` | `-bootstrap` | — | Boot class, configs, global exception handling |
| `framework` | `-framework` | — | Framework extensions |

**Critical constraint:** `service` layer must contain **no SQL or middleware code**.

## Step 1 — Discover Repository Layout

```bash
# Find all independent Git repos under project root
find /path/to/project -maxdepth 2 -name ".git" -type d

# Verify there is NO root .git directory
ls /path/to/project/.git 2>/dev/null || echo "No root repo — multi-repo layout confirmed"
```

If there IS a root `.git`, use a single `core.hooksPath` instead of per-module hooks.

## Step 2 — Create the Structure Checker

Write `scripts/check-structure.py` (see `templates/check-structure.py`). Key rules:

1. **Package prefix rule:**
   - `service` submodules → must start with `com.yonyou.dcs.`
   - All others (`api`, `app`, `infrastructure`, `bootstrap`, `framework`) → must start with `com.yonyou.oem.`

2. **Layer responsibility rule:**
   - `service` files → no MyBatis, Spring JDBC, Redis, MQ imports; no `@Repository`/`@Mapper`
   - `api` files → no `@Controller`/`@RestController`/`@Service`/`@Repository`/`@Mapper`

3. **Package-path consistency:** `package` declaration must match directory structure under `src/main/java`

4. **Cwd-aware path resolution:** When run as a pre-commit hook inside a submodule, resolve paths relative to `os.getcwd()`, not a hardcoded project root.

## Step 3 — Create the Auto-Add Monitor

Write `scripts/watch-auto-add.py` (see `templates/watch-auto-add.py`). Design decisions:

- **Polling, not inotify:** Native file watchers (`watchdog`, `fswatch`) are often unavailable in dev environments. Use a 5-second `git status` polling loop.
- **Multi-repo aware:** Discover all `.git` directories under the project root; iterate over each repo independently.
- **Seen-file deduplication:** Track already-checked files per repo to avoid spamming repeated warnings.
- **Non-blocking:** Print warnings to terminal; never interrupt the developer.
- **Never commit/push:** Only `git add`. Explicitly document this behavior.

## Step 4 — Create the Pre-Commit Hook

Write `.githooks/pre-commit` (see `templates/pre-commit`). Behavior:

1. Auto `git add` any unstaged changes before commit
2. Run `check-structure.py --git-staged` on newly added (diff-filter=A) Java files
3. If violations found → **block commit** and print:
   ```
   ⚠️  pre-commit: 发现规范问题，已阻止 commit。
      如果确认无误，可使用: git commit --no-verify -m '...'
   ```
4. Hook derives `PROJECT_ROOT` from the hook's location (`../../` from `.git/hooks/`)

## Step 5 — Install Hooks to All Modules

```bash
cd /path/to/project
for dir in module-a module-b module-c; do
  if [ -d "$dir/.git/hooks" ]; then
    cp .githooks/pre-commit "$dir/.git/hooks/pre-commit"
    chmod +x "$dir/.git/hooks/pre-commit"
    echo "✅ $dir"
  fi
done
```

**Do NOT use `git config core.hooksPath`** — it only works for single-repo setups. For multi-repo, copy the hook into each module's `.git/hooks/`.

## Step 6 — Document in Project Rules

Update both `CLAUDE.md` (agent-facing) and `AGENTS.md` (build/runtime reference) with:
- Submodule package table
- Layer constraints
- Hook installation/reinstall instructions
- `watch-auto-add.py` usage

## Pitfalls

| Pitfall | Why it happens | Fix |
|---------|---------------|-----|
| `core.hooksPath` fails | Project has multiple independent Git repos, no root `.git` | Copy hook to each `.git/hooks/` |
| `watchdog`/`fswatch` missing | Not installed in dev environment | Use polling-based `watch-auto-add.py` |
| Hook checks historical files | Script scans all staged files instead of diff-filter=A | Use `--diff-filter=A` for new files only |
| Paths resolve to wrong repo | `check-structure.py` hardcodes `ROOT_DIR` | Use `os.getcwd()` for hook invocation |
| Commit blocked by legacy code | Old files violate new rules | Only check **newly added** files (diff-filter=A) |
| User confused by `--no-verify` | They don't know the escape hatch | Always print `git commit --no-verify` hint on failure |
| AGENTS.md corrupted during patching | Partial read (`offset`/`limit`) then overwrite | Always re-read the **entire** file before writing |

## Testing the Setup

```bash
# 1. Verify checker on a known-good file
python3 scripts/check-structure.py path/to/ValidService.java
# Expected: exit 0, no output

# 2. Verify checker on a bad file (wrong package prefix in service layer)
python3 scripts/check-structure.py path/to/BadFile.java
# Expected: exit 1, colored issue list

# 3. Test pre-commit hook manually
cd module-a
bash .git/hooks/pre-commit
# Expected: passes or fails with clear message

# 4. Start background monitor
python3 scripts/watch-auto-add.py
# Create a new Java file → should auto-add and print check results
```

## Variations

**Single-repo monorepo:** Use `git config core.hooksPath .githooks` instead of per-module copies.

**Different package conventions:** Adjust the `expected_prefix` map in `check-structure.py`.

**Additional forbidden patterns:** Extend the `forbidden_patterns` lists in `check-structure.py` (e.g., ban specific utility classes in certain layers).

**IDE integration:** Run `check-structure.py` as an external tool in IntelliJ / VS Code on file save.
