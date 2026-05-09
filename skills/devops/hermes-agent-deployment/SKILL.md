---
name: hermes-agent-deployment
description: "Deploy and configure Hermes Agent's advanced features (L3-L7): skill curation, automated backup, Kanban multi-agent task management, memory provider setup, and MCP server integration."
version: 1.0.0
metadata:
  hermes:
    tags: [hermes, deployment, l3-l7, kanban, mcp, automation, cron, backup]
    related_skills: [hermes-agent, kanban-orchestrator, kanban-worker]
---

# Hermes Agent L3-L7 Advanced Deployment

This skill covers the full "production-grade" Hermes setup:
- **L3** Skill management & auto-cleanup (Curator)
- **L4** Automated backup to private Git repository
- **L5** Kanban task board with multi-agent dispatch
- **L6** Long-term memory provider configuration
- **L7** MCP server integration (Claude Desktop, etc.)

Target environment: macOS local install or VPS.

---

## Pre-flight checks

```bash
# Verify Hermes is installed and up to date
hermes --version
hermes doctor
hermes update   # if behind

# Check current toolset status
hermes tools list
```

Ensure these are enabled: `todo`, `delegation`, `cronjob`, `memory`, `skills`.

---

## L3 — Skill Curator (Auto-cleanup)

Hermes has no built-in Curator. Use a custom Python script + cron job.

### 1. Create curator script

Use the script at `scripts/hermes-curator.py` (bundled with this skill). It:
- Scans `~/.hermes/skills/` for local skills
- Archives skills whose `SKILL.md` hasn't been modified in 60+ days
- Moves them to `~/.hermes/skills/.archive/`
- Reports how many active skills remain (helps monitor token pressure)

### 2. Schedule weekly run

```bash
hermes cron create "0 2 * * 0" \
  --name skill-curator \
  --script scripts/hermes-curator.py \
  --no-agent
```

> **No-agent mode** (`--no-agent`) is preferred for watchdog / cleanup scripts — it skips the LLM entirely and delivers the script's stdout directly.

**Pitfall — passing a prompt with `--script` + `--no-agent`:**
Do NOT add an extra positional argument after `--no-agent`. This is **wrong**:
```bash
hermes cron create "0 2 * * 0" --name skill-curator --script scripts/curator.py --no-agent "some prompt here"
# → error: unrecognized arguments
```

When `--script` + `--no-agent` are used, the script IS the job. There is no LLM prompt.

### 3. Manual run

```bash
python3 ~/.hermes/scripts/hermes-curator.py
```

**Pitfall:** Do NOT archive builtin skills (they live in the source tree, not `~/.hermes/skills/`). The script handles this by only scanning under `~/.hermes/skills/`.

---

## L4 — Automated Backup

### 1. Initialize Git repo in `~/.hermes/`

```bash
cd ~/.hermes

# Create .gitignore (secrets + large files + sessions/logs)
cat > .gitignore << 'EOF'
# Large directories
checkpoints/
hermes-agent/
sessions/
logs/
state-snapshots/
bin/
cache/
images/

# Databases (large, auto-generated)
state.db
state.db-wal
state.db-shm
memory_store.db*
kanban.db

# Secrets
.env
auth.json

# Cache
audio_cache/
__pycache__/
*.pyc

# Large model files
*.gguf
*.bin
models_dev_cache.json
EOF

git init
git add .gitignore
git commit -m "init: Hermes backup repo"
```

**Pitfall — `git add -A` times out:** The `~/.hermes/` directory can contain multi-gigabyte subdirectories (`checkpoints/`, `hermes-agent/`, `sessions/`). Always create `.gitignore` **before** running `git add`, otherwise `git add -A` will scan everything and hang.

**Pitfall — `git rm -r --cached .` resets tracking:** Running this cancels tracking for ALL files (including `.gitignore`), leaving the repo in a confusing state. If you need to re-stage, prefer selective `git add` of specific files instead.

### 2. Configure remote

Use SSH (not HTTPS) to avoid credential prompts:

```bash
git remote add origin git@github.com:<USER>/<REPO>.git
git branch -M main
```

**Pitfall — SSH key not registered:** `git push` fails with "Permission denied (publickey)". Fix:
1. `cat ~/.ssh/id_ed25519.pub`
2. Paste into https://github.com/settings/keys
3. Verify: `ssh -T git@github.com`
4. Then: `git push -u origin main`

**Pitfall — DNS poisoning blocks SSH:** In some networks (especially CN), `github.com` resolves to a bogus IP (e.g., `28.0.0.150`) and `ssh -T git@github.com` times out. Workaround:

```bash
# Switch to HTTPS remote
git remote set-url origin https://github.com/<USER>/<REPO>.git

# Use a Personal Access Token (Classic, scope: repo)
# Generate at https://github.com/settings/tokens/new
git config --global credential.helper store
echo "https://<USER>:<TOKEN>@github.com" > ~/.git-credentials

# Push once to cache credentials
git push -u origin main
```

> **Security note:** `credential.helper store` saves the token in plaintext at `~/.git-credentials`. Switch back to SSH once DNS is clean, then `rm ~/.git-credentials`.

### 3. Create backup script

Use the bundled `scripts/hermes-backup.sh`. It commits all changes daily and pushes if remote exists.

### 4. Schedule daily backup

```bash
hermes cron create "0 3 * * *" \
  --name daily-backup \
  --script scripts/hermes-backup.sh \
  --no-agent
```

---

## L5 — Kanban Multi-Agent Task Board

### 1. Initialize

```bash
hermes kanban init
hermes kanban boards list   # default board is auto-created
```

### 2. Gateway requirement

The Kanban dispatcher lives inside the **gateway**. It ticks every 60 seconds by default.

```bash
hermes gateway start     # start background service
hermes gateway status    # verify it's running
```

**Pitfall — stale service definition:** On macOS, if `hermes gateway status` reports "Service definition is stale relative to the current Hermes install", the embedded dispatcher may not load. Workaround: create a cron-based dispatch loop:

```bash
hermes cron create "*/2 * * * *" \
  --name kanban-dispatch \
  --script scripts/kanban-dispatch.sh \
  --no-agent
```

See bundled `scripts/kanban-dispatch.sh`.

### 3. Create and assign tasks

```bash
hermes kanban create "Task title" \
  --assignee default \
  --body "Detailed instructions"
```

### 4. Monitor

```bash
hermes kanban list          # all tasks
hermes kanban dispatch      # manual dispatch pass
hermes kanban tail <id>     # follow task events
```

For full orchestration patterns (fan-out, review loops, human-in-the-loop), load the `kanban-orchestrator` skill.

---

## L6 — Long-Term Memory Provider

### Check available plugins

```bash
hermes memory status
```

### Switch provider

```bash
hermes config set memory.provider holographic   # or: mem0, honcho, hindsight
```

Options:
- `hindsight` — built-in, always available
- `holographic` — local, structured memory
- `mem0` — external API (needs key)
- `honcho` — external API (needs key)

Verify: `hermes memory status`

---

## L7 — MCP Server Integration

### Expose Hermes as an MCP server

```bash
hermes mcp serve
```

This starts Hermes in MCP server mode, exposing all tools (terminal, file, web, etc.) to compatible clients.

### Claude Desktop (macOS)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hermes": {
      "command": "/Users/<USER>/.local/bin/hermes",
      "args": ["mcp", "serve"]
    }
  }
}
```

**Restart Claude Desktop** (`Cmd+Q`, then reopen) for changes to take effect.

### Other MCP clients

Use the same JSON config structure. The Hermes MCP server runs as a stdio process and registers all available toolsets.

---

## L2 — Chat Platform Integration (Feishu/Lark)

### Overview

Connect Hermes to a messaging platform so it can receive and reply to messages. Currently tested with **Feishu/Lark** (websocket mode).

**Critical config structure:** Feishu credentials MUST be under `platforms.feishu.extra.*`, NOT at the top level. The `hermes config set feishu.app_id X` command puts keys in the wrong place — use the explicit path below.

### 1. Prerequisites

- Feishu self-built app (create at https://open.feishu.cn/app)
- App has **Bot** capability enabled (add via **添加应用能力 → 机器人**)
- App published (via **版本管理与发布 → 创建版本 → 发布**)

### 2. Configure Hermes Gateway

```bash
# CORRECT — keys go under platforms.feishu.extra.*
hermes config set platforms.feishu.enabled true
hermes config set platforms.feishu.extra.app_id "cli_xxxxxxxx"
hermes config set platforms.feishu.extra.app_secret "xxxxxxxx"
hermes config set platforms.feishu.extra.connection_mode "websocket"

# WRONG — these put keys at top level (will be ignored)
hermes config set feishu.app_id "cli_xxxxxxxx"      # ❌
hermes config set feishu.app_secret "xxxxxxxx"      # ❌
```

### 3. Allow all users (for testing)

```bash
# Add to ~/.hermes/.env
echo "GATEWAY_ALLOW_ALL_USERS=true" >> ~/.hermes/.env
```

For production, use platform-specific allowlists instead:
```bash
hermes config set platforms.feishu.extra.allowed_users "ou_xxx1,ou_xxx2"
```

### 4. Verify connection

```bash
hermes gateway restart
sleep 5
cat ~/.hermes/gateway_state.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
p=d.get('platforms',{}).get('feishu',{})
print('State:', p.get('state','?'))
"

# Check WebSocket logs
tail -50 ~/.hermes/logs/gateway.log | grep -i "feishu\|lark\|connect"
```

Expected: `"state": "connected"` and log lines like `[Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2`

### 5. Test in Feishu

1. Open Feishu, search for your bot by app name
2. Send a direct message (e.g., `你好`)
3. Bot should reply

**If no reply:**
- Check `tail -100 ~/.hermes/logs/gateway.log | grep -i "feishu\|error\|denied"` for permission/auth errors
- Verify app has **机器人** capability enabled and is **published**
- Verify the Feishu app's **事件订阅** has "使用长连接接收事件" (WebSocket mode, no public URL needed)

### Switching platforms

The same pattern applies for other platforms (Telegram, Discord, Slack, etc.) — credentials go under `platforms.<name>.extra.*`. Check `hermes gateway setup` for interactive platform configuration.

---

## Verification checklist

After configuring all layers:

```bash
# L3
hermes cron list | grep curator
python3 ~/.hermes/scripts/hermes-curator.py

# L4
cd ~/.hermes && git log --oneline -1
hermes cron list | grep backup

# L5
hermes kanban list
hermes gateway status

# L6
hermes memory status

# L7
hermes mcp list
```

---

## Support files

- `scripts/hermes-curator.py` — Skill cleanup script
- `scripts/hermes-backup.sh` — Daily backup script
- `scripts/kanban-dispatch.sh` — Kanban dispatcher cron wrapper
- `references/feishu-setup.md` — Feishu/Lark platform integration guide
