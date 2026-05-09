User is developing a desktop music player app (Tauri + React) at /Users/luoyang/Desktop/MusicPlayer. UI reference: NetEase Cloud Music style (dark theme, #EC4141 red accent, modern minimalist). Features: local + online music playback. Preferred stack: Tauri (not Electron or Python).
§
Hermes Chinese LLM config pitfall: Kimi/Moonshot 需要 `model.base_url=https://api.moonshot.cn/v1`（不是 MiniMax 的）。Provider 用 `custom` 比 `kimi-coding` 更可靠。`hermes doctor` 对中国 providers 的检查有 false negative，实际 API 可用。
§
Hermes Agent 在中国网络环境下的实际坑：1) GitHub SSH (git@github.com) 常被 DNS 污染导致超时，备份时应退回到 HTTPS + Personal Access Token。2) Hermes gateway 内置的 kanban dispatcher 可能因版本旧而不加载，需用 cron 每 2 分钟运行 `hermes kanban dispatch` 作为 workaround。
§
Environment has NODE_ENV=production set globally. This causes npm to skip devDependencies, which broke Hermes web UI build (TypeScript missing). Must unset before npm install in Hermes repo.