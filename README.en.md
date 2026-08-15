# WorkBuddy Cross-Device Migration Guide

> Migrate WorkBuddy data (conversation history, memory, skills, workspaces) between
> two computers without hitting the "empty conversation list" or "missing work directory" traps.

---

## Background

WorkBuddy stores its data across multiple subdirectories under `~/.workbuddy/`.
Copying the whole folder is NOT enough. Key facts:

- **The conversation list index lives in the `sessions` table of `workbuddy.db`** (most commonly missed)
- **Conversation content lives in `projects/*.jsonl`** (one file per conversation)
- **The work directory (workDir) is recorded in the db**, and **`projects/` directory names are derived from workDir**

Missing any of these results in an empty conversation list or "work directory missing" errors.

## Common Problems

| Symptom | Cause |
|---|---|
| Empty conversation list | `workbuddy.db` (session list source) not restored |
| List shows but opens empty | `projects/*.jsonl` (conversation content) not restored |
| "Work directory may have been renamed or deleted" | `sessions.cwd` points to a path that doesn't exist on the target (e.g. different Windows usernames) |
| Merged list shrinks after restart | Modifying `workbuddy.db` while WorkBuddy is running gets overwritten by WAL |

## Quick Start

### 0. Prerequisites

- Two Windows machines (source + target)
- Python 3 on the target (for the merge scripts)
- Transfer medium: USB / cloud drive / ToDesk file transfer / private GitHub repo

### 1. Package on the source machine

Zip the following from the **source machine**:

```
profile/                          # MEMORY.md, SOUL.md, IDENTITY.md, USER.md, skills/
wb-data/projects/                 # conversation content (*.jsonl)  ★ required
wb-data/workbuddy.db              # session list source             ★ required (most missed)
wb-data/app/sessions.json         # session index
wb-data/{blobs,artifact-index,edge-sync-mapping.db}  # attachments / artifacts / mappings
workspace/                        # workspace code + .workbuddy/memory
```

> Full checklist (including what NOT to copy) in `references/workbuddy-storage-layout.md`.

### 2. Transfer

USB, cloud drive, ToDesk file transfer, or GitHub private repo (clone/pull) — depending on your network.

### 3. Restore base data on the target

```bash
robocopy <extracted>\profile  %USERPROFILE%\.workbuddy  /E
robocopy <extracted>\wb-data  %USERPROFILE%\.workbuddy  /E
robocopy <extracted>\workspace  %USERPROFILE%\WorkBuddy\<workspace-dir>  /E
```

### 4. Merge session lists (optional, if both machines have sessions)

```bash
python scripts/merge_workbuddy_db.py ^
  <source_db> %USERPROFILE%\.workbuddy\workbuddy.db --out %USERPROFILE%\.workbuddy\workbuddy.db.merged
```

### 5. Fix workDir paths

If the two machines have different Windows usernames (e.g. `OLD_USERNAME` vs `NEW_USERNAME`),
session workDirs point to source-machine paths. Run:

```bash
python scripts/fix_workdirs.py %USERPROFILE%\.workbuddy\workbuddy.db.merged ^
  --old-user OLD_USERNAME --new-user NEW_USERNAME
```

This script does three things automatically:
1. Fixes the `cwd` path of every session in the db
2. Creates the corresponding workspace directories
3. **Renames `projects/` directories accordingly** (names derive from workDir — skipping this breaks content loading)

### 6. Replace the database (critical step)

> ⚠️ **Modifying `workbuddy.db` while WorkBuddy is running gets overwritten by the WAL mechanism!**

1. **Fully quit WorkBuddy** (close window + exit from tray icon)
2. Backup: `copy %USERPROFILE%\.workbuddy\workbuddy.db workbuddy.db.bak`
3. Replace: `copy workbuddy.db.merged workbuddy.db`
4. Delete cache: `del workbuddy.db-wal workbuddy.db-shm` (if present)
5. Reopen WorkBuddy → verify the conversation list

### 7. Verify

```sql
SELECT id, cwd, title FROM sessions WHERE deleted_at IS NULL;
-- confirm cwd dirs exist, projects dir names match cwd, jsonl files present
```

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition (for WorkBuddy to invoke automatically) |
| `scripts/merge_workbuddy_db.py` | Merge session lists from two machines |
| `scripts/fix_workdirs.py` | Fix workDir paths + rename projects dirs in sync |
| `references/workbuddy-storage-layout.md` | Storage layout details + troubleshooting table |

## Pitfalls

- **The conversation list source is the `sessions` table of `workbuddy.db`**, not `sessions.json`
- **`projects/` directory names derive from workDir** — renaming cwd requires renaming dirs
- **workDir must actually exist**, otherwise opening a conversation reports "work directory missing"
- **db replacement requires WorkBuddy fully quit** (WAL overwrite)
- **.bat files with Chinese characters get mangled by GBK** — use pure ASCII if delivering .bat
- **git protocol v2 may silently fail** (e.g. direct connection overseas): use `git -c protocol.version=1` or download the zipball instead

## License

MIT
