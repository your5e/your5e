# Notebook Sync

This document specifies the sync algorithm. The reference implementation is
`sync-notebook.sh` and `subsequent_sync.bats` contains test scenarios that any sync
client should handle — use them to verify your implementation.

The one-line summary: local changes always take precedence over remote changes.

The server both keeps deleted files for a while and keeps previous versions of
files, so pushing old changes is never wholly destructive. This does put the
burden of merging changes onto the user, unfortunately. But to start simple
keeps the service reliable and predictable.

The algorithm to sync the local directory is:

1.  _POST_ new local files (not in the cache).
2.  _PUT_ changed local files (differ from the cache). Warn if the server
    reports a different previous version than the cached hash (conflict).
3.  _DELETE_ any deleted files (in the cache, no longer in the directory).
4.  Update the local cache to reflect this, either as a separate step or
    after each individual operation.
5.  _GET_ remote state of the notebook.
7.  _mv_ any files where the remote UUID now has a different filename.
6.  _GET_ any files where the local hash matches, but the server's hash
    has changed (remote updates).
8.  _rm_ any files deleted remotely (any local edits will have already
    un-deleted them in step 2).
9.  Cache the new state, either as a separate step or after each individual
    operation.

If any HTTP request during sync fails, the sync should be abandoned and
retried later.

## Sync Test Matrix

### `first_sync.bats`

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

### `subsequent_sync.bats`

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
| content update, filename update | ✔️ | ✔️ | | ✔️ | ✔️ | | | |
| filename update swapped | ✔️ | ✔️ | | | ✔️ | | | |
| filename update chain | ✔️ | ✔️ | | | ✔️ | | | |
| filename update chain, reversed | ✔️ | ✔️ | | | ✔️ | | | |
| filename update cycle | ✔️ | ✔️ | | | ✔️ | | | |
| filename update cycle, local modification blocks cycle | ✔️ | ❌ | ✔️ | | ✔️ | | | |
| filename update cycle, untracked file blocks cycle | ✔️ | ❌ | ✔️ | | ✔️ | | | |
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
