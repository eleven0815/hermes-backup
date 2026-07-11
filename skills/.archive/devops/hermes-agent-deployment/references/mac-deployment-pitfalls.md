# macOS Hermes L3-L7 Deployment Pitfalls

Session-derived fixes from real deployment on macOS (2026-05-09).

---

## GitHub Push over SSH

**Symptom:** `git push -u origin main` fails with:
```
git@github.com: Permission denied (publickey).
```

**Root cause:** The SSH key (`~/.ssh/id_ed25519.pub`) exists locally but is NOT registered on the GitHub account.

**Fix:**
1. `cat ~/.ssh/id_ed25519.pub` → copy output
2. Open https://github.com/settings/keys → New SSH key → paste → Add
3. Verify: `ssh -T git@github.com`
4. Then push: `git push -u origin main`

---

## GitHub Push blocked by DNS poisoning

**Symptom:** `ssh -T git@github.com` times out. `nslookup github.com` returns a bogus IP like `28.0.0.150`.

**Root cause:** Network-level DNS hijacking (common in some regions) resolves `github.com` to a non-GitHub IP, breaking SSH.

**Fix — fallback to HTTPS + PAT:**

```bash
# Switch remote to HTTPS
cd ~/.hermes
git remote remove origin 2>/dev/null
git remote add origin https://github.com/<USER>/<REPO>.git

# Configure credential storage
git config --global credential.helper store

# Create token at https://github.com/settings/tokens/new (Classic, scope: repo)
# Then cache it
echo "https://<USER>:<TOKEN>@github.com" > ~/.git-credentials

# Push
git push -u origin main
```

**Cleanup once DNS is clean:**
```bash
git remote set-url origin git@github.com:<USER>/<REPO>.git
rm ~/.git-credentials
```

---

## Cron `--no-agent` argument order

**Symptom:**
```bash
hermes cron create "0 2 * * 0" --name skill-curator --script scripts/curator.py --no-agent "weekly cleanup"
# → error: unrecognized arguments: weekly cleanup
```

**Root cause:** When `--script` + `--no-agent` are both present, the script IS the job. A trailing positional "prompt" argument is not expected.

**Fix:** Drop the prompt.
```bash
hermes cron create "0 2 * * 0" --name skill-curator --script scripts/curator.py --no-agent
```

---

## `git add -A` hangs on large `~/.hermes/`

**Symptom:** `git add -A` or `git status` takes minutes or times out.

**Root cause:** `~/.hermes/` contains multi-gigabyte directories (`checkpoints/`, `hermes-agent/`, `sessions/`, `state-snapshots/`, `bin/`). Git scans them even if they are untracked.

**Fix:** Create `.gitignore` **before** any `git add`. Exclude large directories explicitly:

```gitignore
# Large directories
checkpoints/
hermes-agent/
sessions/
logs/
state-snapshots/
bin/
cache/
images/

# Databases
state.db*
memory_store.db*
kanban.db
```

**Avoid `git rm -r --cached .`** — it untracks everything (including `.gitignore`) and forces you to re-stage from scratch. Use selective `git add <path>` instead.

---

## Kanban Gateway Dispatcher Not Auto-Dispatching

**Symptom:** Tasks stay in `ready` forever. `hermes kanban create` warns:
```
⚠  No gateway is running — the task will sit in 'ready' until you start it.
```

But `hermes gateway status` shows the gateway PID exists.

**Root cause:** On macOS with an older/stale launchd plist, the gateway starts but the embedded Kanban dispatcher module doesn't load (version mismatch or missing feature in older binary).

**Fix — cron-based dispatch workaround:**

```bash
hermes cron create "*/2 * * * *" \
  --name kanban-dispatch \
  --script scripts/kanban-dispatch.sh \
  --no-agent
```

This runs `hermes kanban dispatch` every 2 minutes, manually ticking the dispatcher even when the gateway's embedded dispatcher is inactive.

**When to remove workaround:** After running `hermes update` and verifying `hermes gateway status` no longer reports "Service definition is stale."

---

## Feishu Config Path — Keys Must Be Under `platforms.feishu.extra.*`

**Symptom:** `hermes gateway status` shows Feishu connected (WebSocket OK) but bot never replies to messages. No error in logs.

**Root cause:** Running `hermes config set feishu.app_id X` writes the key at YAML top level (`feishu.app_id: X`), but the Feishu adapter reads from `platforms.feishu.extra.app_id`. These are different locations.

**Fix — correct path:**
```bash
hermes config set platforms.feishu.enabled true
hermes config set platforms.feishu.extra.app_id "cli_xxxxxxxx"
hermes config set platforms.feishu.extra.app_secret "xxxxxxxx"
hermes config set platforms.feishu.extra.connection_mode "websocket"
```

**Verify:**
```bash
grep -A5 "feishu:" ~/.hermes/config.yaml
# Should show:
# feishu:
#   app_id: ...
# (top-level) WRONG — adapter won't see it
# vs
# platforms:
#   feishu:
#     enabled: true
#     extra:
#       app_id: ...   CORRECT
```

**Also:** The app must have Bot capability enabled AND be published (not just saved as a draft). Check with:
```bash
TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_xxx","app_secret":"xxx"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('tenant_access_token',''))")

curl -s "https://open.feishu.cn/open-apis/bot/v3/info" \
  -H "Authorization: Bearer $TOKEN"
# Expected: "activate_status": 2  (2 = activated)
# If code=11205: "app do not have bot" → enable bot capability in developer console and republish
```

Before deploying L3-L7, ensure Hermes is current:
```bash
hermes update
```

The session started with `v0.13.0` which was **89 commits behind**. Many Kanban and MCP features are actively developed — running stale versions causes subtle dispatcher issues.
