---
name: apple-reminders
description: "Apple Reminders via remindctl: add, list, complete."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Reminders, tasks, todo, macOS, Apple]
prerequisites:
  commands: [remindctl]
---

# Apple Reminders

Use `remindctl` to manage Apple Reminders directly from the terminal. Tasks sync across all Apple devices via iCloud.

## Prerequisites

- **macOS** with Reminders.app
- Install: `brew install steipete/tap/remindctl`
- **First-time authorization required** (see Troubleshooting below)
- Check: `remindctl status`

### Permission Denied / Command Timeout

If `remindctl` or `osascript` commands **timeout or hang** when accessing Reminders, macOS is blocking automation access. Commands will hang indefinitely rather than giving clear errors — this is the diagnostic signal.

1. Open **System Settings > Privacy & Security > Automation** (or search "Automation")
2. Find **Terminal** (or your terminal app / Hermes Agent process)
3. Enable **Reminders** access
4. Alternatively: open the Reminders app manually to trigger the system permission prompt

After authorization, commands complete instantly.

### Fallback: Direct osascript

If `remindctl` continues having issues, use osascript directly:

```bash
# Create list if needed
osascript -e 'tell application "Reminders" to make new list with properties {name:"mac"}'

# Add reminder
osascript -e 'tell application "Reminders"
    set targetList to first list whose name is "mac"
    make new reminder at end of targetList with properties {name:"Task title"}
end tell'

# Set date/time and notes
osascript -e 'tell application "Reminders"
    set r to first reminder whose name contains "Task title"
    set due date of r to date "2026年4月29日 9:30:00"
    set body of r to "地点: 国际事业部-14-3 塞纳河"
end tell'
```

### Date Format Note

On Chinese locale systems (`LC_TIME=zh_CN.UTF-8`), osascript requires Chinese date format:
- Works: `date "2026年4月29日 9:30:00"`
- Fails: `date "April 29, 2026 9:30 AM"`

## When to Use

- User mentions "reminder" or "Reminders app"
- Creating personal to-dos with due dates that sync to iOS
- Managing Apple Reminders lists
- User wants tasks to appear on their iPhone/iPad

## When NOT to Use

- Scheduling agent alerts → use the cronjob tool instead
- Calendar events → use Apple Calendar or Google Calendar
- Project task management → use GitHub Issues, Notion, etc.
- If user says "remind me" but means an agent alert → clarify first

## Quick Reference

### View Reminders

```bash
remindctl                    # Today's reminders
remindctl today              # Today
remindctl tomorrow           # Tomorrow
remindctl week               # This week
remindctl overdue            # Past due
remindctl all                # Everything
remindctl 2026-01-04         # Specific date
```

### Manage Lists

```bash
remindctl list               # List all lists
remindctl list Work          # Show specific list
remindctl list Projects --create    # Create list
remindctl list Work --delete        # Delete list
```

### Create Reminders

```bash
remindctl add "Buy milk"
remindctl add --title "Call mom" --list Personal --due tomorrow
remindctl add --title "Meeting prep" --due "2026-02-15 09:00"
```

### Complete / Delete

```bash
remindctl complete 1 2 3          # Complete by ID
remindctl delete 4A83 --force     # Delete by ID
```

### Output Formats

```bash
remindctl today --json       # JSON for scripting
remindctl today --plain      # TSV format
remindctl today --quiet      # Counts only
```

## Date Formats

Accepted by `--due` and date filters:
- `today`, `tomorrow`, `yesterday`
- `YYYY-MM-DD`
- `YYYY-MM-DD HH:mm`
- ISO 8601 (`2026-01-04T12:34:56Z`)

## Rules

1. When user says "remind me", clarify: Apple Reminders (syncs to phone) vs agent cronjob alert
2. Always confirm reminder content and due date before creating
3. Use `--json` for programmatic parsing
