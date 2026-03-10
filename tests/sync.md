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
6.  _mv_ any files where the remote UUID now has a different filename.
7.  _GET_ any files where the local hash matches, but the server's hash
    has changed (remote updates).
8.  _rm_ any files deleted remotely (any local editeds will have already
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

| Test                    | Local | Remote | Content | Filename |
|-------------------------|-------|--------|---------|----------|
| empty directory         | —     | file   |         |          |
| local files             | file  | file   | ❌      | ✔️       |
| local matches remote    | file  | file   | ✔️      | ✔️       |
| local file clashes      | file  | dir    |         |          |
| local dir clashes       | dir   | file   |         |          |
| case collision          | file  | file   | ❌      | ❌       |
| case collision, matches | file  | file   | ✔️      | ❌       |

### `subsequent_sync.bats`

- **Tracked** — file is in .sync-state from previous sync
- **Local Edited** — local content differs from cached hash
- **Local Renamed** — local file has been moved to a different path
- **Local Deleted** — local file no longer exists
- **Remote Edited** — server content hash differs from cached
- **Remote Renamed** — server filename differs from cached
- **Remote Deleted** — server has soft-deleted the file
- **Stale** — tracked UUID no longer exists on server

| Test | Tracked | Local Edited | Local Renamed | Local Deleted | Remote Edited | Remote Renamed | Remote Deleted | Stale |
|------|---------|--------------|---------------|---------------|---------------|----------------|----------------|--------|
| no change | ✔️ | | | | | | | |
| untracked file | | | | | | | | |
| untracked file, local edited, directory | | ✔️ | | | | | | |
| untracked file, local edited | | ✔️ | | | | | | |
| untracked file, remote renamed | | | | | | ✔️ | | |
| untracked file, local edited, remote renamed | | ✔️ | | | | ✔️ | | |
| remote edited | ✔️ | | | | ✔️ | | | |
| remote renamed | ✔️ | | | | | ✔️ | | |
| remote renamed, local edited, directory | ✔️ | ✔️ | | | | ✔️ | | |
| remote edited, remote renamed | ✔️ | | | | ✔️ | ✔️ | | |
| remote renamed, swapped | ✔️ | | | | | ✔️ | | |
| remote renamed, chain | ✔️ | | | | | ✔️ | | |
| remote renamed, chain reversed | ✔️ | | | | | ✔️ | | |
| remote renamed, cycle | ✔️ | | | | | ✔️ | | |
| remote renamed, cycle, local edited | ✔️ | ✔️ | | | | ✔️ | | |
| remote renamed, cycle, untracked file | ✔️ | | | | | ✔️ | | |
| local edited | ✔️ | ✔️ | | | | | | |
| local edited, remote edited | ✔️ | ✔️ | | | ✔️ | | | |
| local edited, remote renamed | ✔️ | ✔️ | | | | ✔️ | | |
| local edited, remote edited, remote renamed | ✔️ | ✔️ | | | ✔️ | ✔️ | | |
| remote deleted | ✔️ | | | | | | ✔️ | |
| remote deleted, local edited | ✔️ | ✔️ | | | | | ✔️ | |
| stale file | ✔️ | | | | | | | ✔️ |
| stale file, remote edited | ✔️ | | | | ✔️ | | | ✔️ |
| stale file, local edited | ✔️ | ✔️ | | | | | | ✔️ |
| stale file, local deleted | ✔️ | | | ✔️ | | | | ✔️ |
| stale file, local deleted, remote edited | ✔️ | | | ✔️ | ✔️ | | | ✔️ |
| local deleted | ✔️ | | | ✔️ | | | | |
| local deleted, remote edited | ✔️ | | | ✔️ | ✔️ | | | |
| local deleted, remote renamed | ✔️ | | | ✔️ | | ✔️ | | |
| local deleted, remote edited, remote renamed | ✔️ | | | ✔️ | ✔️ | ✔️ | | |
| local deleted, local edited, remote edited, remote renamed | ✔️ | ✔️ | | ✔️ | ✔️ | ✔️ | | |
| local deleted, remote deleted | ✔️ | | | ✔️ | | | ✔️ | |
