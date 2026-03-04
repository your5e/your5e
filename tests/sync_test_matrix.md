# Sync Test Matrix

## First Sync

- **Local** — what exists locally: nothing, file, or dir
- **Remote** — what remote wants: file or dir
- **Content** — local and remote file content matches
- **Filename** — local and remote filename matches

| Test |  Local | Remote | Content | Filename |
|------|--------|--------|---------|----------|
| first sync to empty directory | — | file | | |
| first sync to non-empty directory preserves all local files | file | file | ❌ | ✔️ |
| first sync local file matches remote | file | file | ✔️ | ✔️ |
| first sync local file without extension blocks remote subdirectory | file | dir | | |
| first sync local directory blocks remote file | dir | file | | |
| first sync case sensitivity collision | file | file | ❌ | ❌ |
| first sync case sensitivity collision, content matches | file | file | ✔️ | ❌ |

## Subsequent Sync

- **Tracked** — file is in .sync-state from previous sync
- **In Sync** — local content matches tracked state from last sync
- **Conflict** — remote wants to write but local state blocks it
- **Content Update** — remote content differs from tracked
- **Filename Update** — remote filename differs from tracked
- **Remote Delete** — remote is soft-deleted
- **Purged** — tracked UUID no longer found on server
- **Local Delete** — local file has been deleted

| Test | Tracked | In Sync | Conflict | Content Update | Filename Update | Remote Deleted | Purged | Local Deleted |
|------|---------|---------|----------|----------------|-----------------|----------------|--------|---------------|
| no change | ✔️ | ✔️ | | | | | | |
| untracked file | | — | | | | | | |
| untracked file blocked by directory | | — | ✔️ | | | | | |
| untracked file, content update | | — | ✔️ | ✔️ | | | | |
| untracked file, filename update | | — | ✔️ | | ✔️ | | | |
| untracked file, content update, filename update | | — | ✔️ | ✔️ | ✔️ | | | |
| content update | ✔️ | ✔️ | | ✔️ | | | | |
| filename update | ✔️ | ✔️ | | | ✔️ | | | |
| filename update blocked by directory | ✔️ | ✔️ | ✔️ | | ✔️ | | | |
| filename update swapped _(skipped)_ | ✔️ | ✔️ | | | ✔️ | | | |
| filename update cycle _(skipped)_ | ✔️ | ✔️ | | | ✔️ | | | |
| content update, filename update | ✔️ | ✔️ | | ✔️ | ✔️ | | | |
| local update | ✔️ | ❌ | | | | | | |
| local update, content update | ✔️ | ❌ | ✔️ | ✔️ | | | | |
| local update, filename update | ✔️ | ❌ | ✔️ | | ✔️ | | | |
| local update, content update, filename update | ✔️ | ❌ | ✔️ | ✔️ | ✔️ | | | |
| remote deleted | ✔️ | ✔️ | | | | ✔️ | | |
| remote deleted, local update | ✔️ | ❌ | ✔️ | | | ✔️ | | |
| stale file | ✔️ | ✔️ | | | | | ✔️ | |
| stale file, content update | ✔️ | ✔️ | ✔️ | ✔️ | | | ✔️ | |
| stale file, local update | ✔️ | ❌ | ✔️ | ✔️ | | | ✔️ | |
| stale file, local delete | ✔️ | ❌ | | | | | ✔️ | ✔️ |
| stale file, local delete, server reuses filename | ✔️ | ❌ | | | | | ✔️ | ✔️ |
| local delete | ✔️ | ❌ | | | | | | ✔️ |
| local delete, content update | ✔️ | ❌ | | ✔️ | | | | ✔️ |
| local delete, filename update | ✔️ | ❌ | | | ✔️ | | | ✔️ |
| local delete, content update, filename update | ✔️ | ❌ | | ✔️ | ✔️ | | | ✔️ |
| local delete, content update, filename update blocked | ✔️ | ❌ | ✔️ | ✔️ | ✔️ | | | ✔️ |
| local delete, remote deleted | ✔️ | ❌ | | | | ✔️ | | ✔️ |
