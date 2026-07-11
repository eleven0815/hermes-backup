---
name: batch-dev-env-setup
description: "Batch-install multiple dev tools from a tutorial/article: multi-repo clone, dependency resolution, native module builds, Python version handling."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dev-env, tooling, setup, installation, toolchain, npm, pnpm, python, venv]
    related_skills: [github-repo-management, systematic-debugging]
---

# Batch Dev Environment Setup

## Overview

User sees a tutorial, article, or list recommending N tools/repos and wants them all installed and running. This skill covers the full pipeline: reading the source, checking the local environment, cloning repos, resolving dependencies, handling native builds, and verifying startup.

## When to Use

Trigger when the user says anything like:
- "Install these tools from this article"
- "Set up the tools mentioned in this tutorial"
- "Clone and configure these repos"
- "Get this dev stack running"
- Any request involving multiple git clones + dependency installs + build steps from a single source of truth (article, README, docs, list).

## The Workflow

### Phase 1: Extract Installation Plan

1. Read the source (web page, article, README) with `browser_navigate` + `browser_snapshot` or `read_file`.
2. Extract every installation command:
   - Global installs: `npm i -g`, `pip install`, `brew install`, `cargo install`
   - Repo URLs to clone
   - Post-clone commands: `npm install`, `pnpm install`, `pip install -r requirements.txt`
   - Build commands: `npm run build`, `pnpm build`, `cargo build`
   - Startup commands: `npm start`, `pnpm dev`, `python app.py`
3. Note environment requirements (Node version, Python version, etc.).

### Phase 2: Environment Check

Run a single probe:

```bash
node --version && npm --version && pnpm --version 2>/dev/null && \
python3 --version && git --version
```

- If a package manager is missing (`pnpm`, `yarn`), install it: `corepack enable` for pnpm, or `npm i -g yarn`.
- If Python is too old for a listed requirement, check for newer Homebrew Pythons: `ls /opt/homebrew/bin/python3.*` or `which python3.11 python3.12 python3.13`.

### Phase 3: Install in Order

**Order matters:**
1. **Global tools first** (fastest, no clone needed).
2. **Git clones** into a unified directory (`mkdir -p ~/hermes-tools` or `~/tools`).
3. **Per-repo dependencies**.
4. **Build steps**.
5. **Startup verification**.

For each repo:

#### Pick the Right Package Manager

| Lockfile present | Use |
|-----------------|-----|
| `pnpm-lock.yaml` | `pnpm install` |
| `yarn.lock` | `yarn install` |
| `package-lock.json` | `npm install` |
| None | Prefer `pnpm install` or `npm install` |

**Critical:** If `npm install` hangs for minutes with a huge `node_modules` but core packages (like `react`, `vite`) are missing, the project likely uses a different lockfile. Kill the process and switch to the correct package manager.

#### Handle Native Module Builds (pnpm)

If you see `[ERR_PNPM_IGNORED_BUILDS]`, approve the native builds:

```bash
pnpm approve-builds better-sqlite3 node-pty sharp esbuild @swc/core @parcel/watcher
```

If a native addon fails at runtime (e.g. `better-sqlite3` NODE_MODULE_VERSION mismatch), rebuild:

```bash
pnpm rebuild better-sqlite3
```

#### Handle Python Dependencies

1. Check the project's Python version requirement (README, `pyproject.toml`, error messages).
2. If system Python is too old, use a newer Homebrew Python (`python3.11`, `python3.13`).
3. On macOS/Homebrew Python, avoid `--break-system-packages`. Create a venv instead:

```bash
python3.13 -m venv ~/.venvs/<tool-name>
source ~/.venvs/<tool-name>/bin/activate
pip install <package>
```

4. If the user later needs to configure a tool to use this venv, provide the full venv python path.

### Phase 4: Build & Verify

After dependencies are resolved:

1. **Build:** Run the build command (`pnpm build`, `npm run build`, etc.).
2. **Check scripts:** If the user asks "how do I start this?", read `package.json` → `scripts`.
3. **Validate binaries:** `which <tool>` and `<tool> --version` for globals.
4. **Summarize:** List what was installed, where, and how to start each component.

## Common Pitfalls

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `npm install` hangs for >3 min, `node_modules` huge but core deps missing | Wrong package manager; project uses pnpm | Kill process, delete `node_modules`, run `pnpm install` |
| `pip install` fails with "externally-managed-environment" | Homebrew Python PEP 668 protection | Use `python3.x -m venv` + activate |
| `pip install` fails with "Requires-Python >=3.10" | System Python too old | Use Homebrew Python 3.11+ |
| `[ERR_PNPM_IGNORED_BUILDS]` after install | pnpm blocks native build scripts | `pnpm approve-builds <pkg1> <pkg2> ...` |
| `better-sqlite3` runtime error / `NODE_MODULE_VERSION` mismatch | Native addon compiled for wrong Node | `pnpm rebuild better-sqlite3` |
| `git clone` timeout | Large repo or slow connection | Increase timeout to 300s or use `--depth 1` |
| No `pip` command found | System uses `python3 -m pip` | Use `python3 -m pip` or `python3.x -m pip` |

## Quick Command Reference

```bash
# Environment probe
node --version && npm --version && pnpm --version && python3 --version && git --version

# Check for newer Python versions (macOS/Homebrew)
ls /opt/homebrew/bin/python3.*

# Create and use a Python venv
python3.13 -m venv ~/.venvs/myenv
source ~/.venvs/myenv/bin/activate
pip install <pkg>

# Fix pnpm native builds
cd <repo>
pnpm approve-builds better-sqlite3 node-pty sharp esbuild
pnpm rebuild better-sqlite3

# Check package scripts
cat package.json | grep -A 10 '"scripts"'
```

## Real-World Example (5-tool Hermes stack)

1. Globals: `npm install -g repomix tokscale`
2. Clone repos into `~/hermes-tools`
3. `hermes-workspace` had `pnpm-lock.yaml` → killed stuck `npm install`, switched to `pnpm install`
4. `hindsight` needed Python 3.10+ → used `python3.13` with venv
5. `mission-control` needed `pnpm approve-builds` for `better-sqlite3`, `node-pty`, `sharp`, `esbuild`, `@swc/core`
6. Verified with `repomix --version`, `tokscale --version`, and `pnpm build`
