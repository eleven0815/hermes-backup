# Feishu/Lark Platform Setup — Session Notes

## What we did (2026-05-09)

Connected Hermes Gateway to Feishu app `cli_a9759cc173b89bc2` for user eleven0815.

### Key lesson — config path matters

Wrong:
```bash
hermes config set feishu.app_id "cli_xxx"        # puts at top-level YAML key "feishu.app_id"
hermes config set feishu.app_secret "xxx"
```

Correct:
```bash
hermes config set platforms.feishu.enabled true
hermes config set platforms.feishu.extra.app_id "cli_xxx"
hermes config set platforms.feishu.extra.app_secret "xxx"
hermes config set platforms.feishu.extra.connection_mode "websocket"
```

The Feishu adapter reads from `cfg.extra` (PlatformConfig.extra dict), not top-level YAML.

### Bot capability must be added and published

- App existed at https://open.feishu.cn/app/cli_a9759cc173b89bc2
- Bot capability was NOT enabled initially → `curl /bot/v3/info` returned `{"code":11205,"msg":"app do not have bot"}`
- Fix: Add application ability → 机器人 → enable → publish new version
- After publishing, `activate_status: 2` confirms bot is active

### Gateway connection check

```bash
# State file
cat ~/.hermes/gateway_state.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
p=d.get('platforms',{}).get('feishu',{})
print('State:', p.get('state'))
"

# WebSocket log
tail -50 ~/.hermes/logs/gateway.log | grep "Lark"
# Expected: [Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2
```

### GATEWAY_ALLOW_ALL_USERS

Set in `~/.hermes/.env` to bypass per-user allowlists during testing:
```
GATEWAY_ALLOW_ALL_USERS=true
```

### Error: "Unable to hydrate bot identity"

Log warning:
```
[Feishu] Unable to hydrate bot identity from application info.
Grant admin:app.info:readonly or application:application:self_manage
```

This is a **warning**, not fatal. The bot still connects and receives messages. It only affects group @mention gating (bot name resolution). For DMs, this is fine.

### DNS poisoning issue (for future SSH pushes)

When SSH to `git@github.com` times out but HTTPS works:
- GitHub DNS resolves to `28.0.0.150` (wrong IP) → SSH fails
- HTTPS (port 443) still works
- Solution: HTTPS + Personal Access Token with `credential.helper store`

Token: `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` (user provided, stored in `~/.git-credentials`)

Switch back to SSH when DNS is clean:
```bash
git remote set-url origin git@github.com:eleven0815/hermes-backup.git
rm ~/.git-credentials
```

## Current status (after session)

- Feishu: `connected` (WebSocket, auto-reconnects every ~90s)
- Bot open_id: `ou_1d2914c841b9791d8461d2b566a533d2`
- App name: Hermes
- Issue: User cannot send messages yet — likely need `im:message` scope or event subscription for DMs

## Troubleshooting: Bot not replying

If Feishu shows `connected` but bot doesn't reply:

1. **Check event subscription mode**: Feishu apps have two event receiving modes:
   - **Webhook** (HTTP): Requires a public URL — not suitable for local/Mac running
   - **WebSocket** (长连接): Works without public URL — enable "使用长连接接收事件" in developer console
   
   In https://open.feishu.cn/app/cli_a9759cc173b89bc2/event :
   - Look for "事件订阅方式" or "接收事件方式"
   - Ensure "长连接" / "WebSocket" mode is selected

2. **Check required scopes**: The app needs at minimum:
   - `im:message` — send messages
   - `im:message.receive_v1` — receive messages
   
   These are added in **权限管理** → search and enable these scopes.

3. **Publish after scope changes**: Any scope change requires re-publishing the app.

4. **Verify DM works**: After making changes, re-publish and test by sending a DM to the bot.

5. **Log check for incoming events**:
   ```bash
   tail -f ~/.hermes/logs/gateway.log | grep -i "feishu\|receive\|incoming\|message_received"
   ```
   If no `[Lark]` lines appear when you send a message in Feishu, the events aren't reaching Hermes — likely a scope or event subscription misconfiguration.
