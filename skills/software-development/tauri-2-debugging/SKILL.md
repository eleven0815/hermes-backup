---
name: tauri-2-debugging
description: "Debug Tauri 2.x desktop apps: command name matching, capabilities config, snake_case vs camelCase, missing backend calls from Zustand stores."
---

# Tauri 2.x Desktop App Debugging

## Trigger
When debugging Tauri 2.x desktop apps where frontend invoke calls fail, commands don't reach backend, or plugin permissions are missing.

## Patterns & Solutions

### 1. Command Name Matching
**Problem:** Frontend `invoke('scan_directory')` fails because backend uses wrong name.

Tauri 2.x command names are the Rust function name directly (no prefix transformation). 

```rust
// WRONG - frontend would call "cmd_scan_directory"
#[tauri::command]
fn cmd_scan_directory(path: String) -> Result<Vec<Song>, String> { ... }

// CORRECT - frontend calls "scan_directory"
#[tauri::command]
fn scan_directory(path: String) -> Result<Vec<Song>, String> { ... }
```

Frontend must match exactly:
```typescript
await invoke('scan_directory', { path });  // NOT 'cmd_scan_directory'
```

### 2. Tauri 2.x Capabilities Configuration
**Problem:** Plugin commands (dialog, shell) fail with permission errors.

Tauri 2.x requires explicit capabilities in `src-tauri/capabilities/` directory.

```json
// src-tauri/capabilities/default.json
{
  "$schema": "https://schema.tauri.app/config/2/capability",
  "identifier": "default",
  "description": "Default permissions for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "dialog:allow-open",
    "shell:allow-open"
  ]
}
```

Required for: dialog plugin, shell plugin, and custom commands.

### 3. Field Naming: Rust snake_case vs TypeScript camelCase
**Problem:** Rust returns `local_path` but TypeScript expects `localPath`.

Rust `#[derive(Serialize)]` uses snake_case by default:
```rust
pub struct Song {
    pub local_path: String,  // Serialized as "local_path"
}
```

Solution: Accept both in TypeScript:
```typescript
interface Song {
  localPath?: string;   // For manual mapping
  local_path?: string;  // Direct from Rust
}
```

Or normalize at the call site:
```typescript
const localPath = song.localPath || (song as any).local_path;
```

### 4. Zustand Store Missing Backend Calls
**Problem:** `playSong` updates UI state but doesn't call backend `playAudio`.

Store actions must explicitly invoke Tauri commands:
```typescript
playSong: async (song: Song) => {
  set({ currentSong: song, isPlaying: true });

  // Must explicitly call backend
  if (song.source === 'local' && song.localPath) {
    await playAudio(song.localPath);
  }
}
```

**Pitfall: Duplicate Zustand Store Definitions**
If a store file exports multiple `create()` calls (e.g., one for defaults, one for a hook), ensure ALL implementations include necessary backend invocations. Search for all occurrences of an action name:
```bash
grep -n "playSong:" src/store/playerStore.ts
```
In the MusicPlayer project, `createStore` had proper backend calls but `usePlayerStore` (the actual hook used) did not — causing silent failures where UI updated but audio didn't play.

### 5. External API Headers (e.g., NetEase Music)
**Problem:** API returns 400 "参数错误" despite correct parameters.

Many Chinese APIs require browser-like headers:
```typescript
fetch(url, {
  headers: {
    'Referer': 'https://music.163.com/',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
  }
});
```

### 6. Tauri Plugin npm Packages Without Rust Counterparts
**Problem:** Error "Plugin not found" or "store.load not allowed" when using `@tauri-apps/plugin-store` or similar.

Many `@tauri-apps/plugin-*` npm packages require corresponding Rust plugins in `Cargo.toml`. If the Rust plugin isn't installed, the npm package fails at runtime.

Solution: Either install the Rust plugin:
```toml
# Cargo.toml
tauri-plugin-store = "2"
```

Or replace with browser alternatives (simpler for most cases):
```typescript
// Instead of @tauri-apps/plugin-store
const store = new LazyStore('data.json');

// Use localStorage instead
localStorage.setItem('key', JSON.stringify(data));
const data = JSON.parse(localStorage.getItem('key') || 'null');
```

Common plugins needing Rust side: `plugin-store`, `plugin-fs`, `plugin-dialog`, `plugin-shell`.

## Verification Steps
1. Check browser DevTools Console for invoke errors
2. Verify command name matches exactly between invoke() and #[tauri::command]
3. Confirm capabilities directory exists with proper permissions
4. Use `cargo build` to ensure Rust compiles without errors
5. For API issues, test with curl + headers first
6. **Rust code changes require full restart** — hot reload only works for Vite/TypeScript changes. After modifying Rust files, kill the process and restart with `npm run tauri dev`.

## Related
- systematic-debugging: General debugging methodology
- node-inspect-debugger: Frontend debugging
