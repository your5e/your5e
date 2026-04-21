# Notebook Sync

This document specifies the sync algorithm. The reference implementation is in
`sync-notebook.sh`. The BATS test files contain scenarios that any sync
client should handle — use them to verify your implementation.

The one-line summary: concurrent edits are merged automatically when possible,
but local changes always take precedence when merging is impossible.

The server both keeps deleted files for a while and keeps previous versions of
files, so pushing old changes is never wholly destructive.

Broadly, the algorithm to sync the local directory is:

1.  _GET_ remote state of the notebook.
2.  Scan for untracked renames (files moved locally outside of sync)
    by matching missing tracked files to untracked files by content hash.
3.  _PATCH_ locally renamed files (cached filename differs from server filename).
4.  _DELETE_ any deleted files (in the cache, no longer in the directory).
5.  _POST_ new local files (not in the cache).
6.  _PUT_ changed local files (differ from the cache). The server will merge
    or replace if the previous version differs from the cached hash. If the
    returned hash differs from the local file (server merged or normalised
    line endings), _GET_ the updated content.
7.  _rm_ any files deleted remotely (any local edits will have already
    un-deleted them in step 6).
8.  _mv_ any files where the remote UUID now has a different filename.
9.  _GET_ any files where the local hash matches, but the server's hash
    has changed (remote updates). This includes files deleted locally but
    updated remotely, restoring them with the new remote content.
10. If both local and remote have changed, _GET_ the common ancestor by
    hash and attempt a three-way merge. If merging fails, keep the local
    version and warn the user.
11. Check for stale files (UUIDs in cache but not on remote) and warn
    the user.

Update the local cache after each successful operation.

Some API errors (400, 401, 404, 409) should be expected and handled, they are
for the user to resolve. Other errors (network failures, 5xx server errors,
authentication problems) should abort the sync for a later retry.

## Incremental vs Full Sync

The API supports incremental changes using the `?since=` parameter, which
should be used to speed up repeated short-term syncs. The implemented sync
engines do this, but also then a full sync every hour to ensure data fidelity.


## Sync Test Matrix

### `first_sync_*.bats`

Test the initial sync completes correctly.

- **Local** — what exists locally: nothing, file, or dir
- **Remote** — what remote wants: file or dir
- **Content** — local and remote file content matches
- **Filename** — local and remote filename matches

| Test | Local | Remote | Content | Filename |
|------|-------|--------|---------|----------|
| empty directory | — | file | | |
| empty notebook | — | — | | |
| local files | file | file | ❌ | ✔️ |
| local matches remote | file | file | ✔️ | ✔️ |
| local file clashes | file | dir | | |
| local dir clashes | dir | file | | |
| hidden files ignored | file | — | | |
| case collision | file | file | ❌ | ❌ |
| case collision, matches | file | file | ✔️ | ❌ |

### `subsequent_sync_*.bats`

Test updating the state from an existing synced directory works.

- **Tracked** — file is in ``.sync-state` from previous sync
- **Local Edited** — local content differs from cached hash
- **Local Renamed** — local file has been moved to a different path
- **Local Deleted** — local file no longer exists
- **Remote Edited** — server content hash differs from cached
- **Remote Renamed** — server filename differs from cached
- **Remote Deleted** — server has soft-deleted the file
- **Stale** — tracked UUID no longer exists on server

| Test | Tracked | Local Edited | Local Renamed | Local Deleted | Remote Edited | Remote Renamed | Remote Deleted | Stale |
|------|---------|--------------|---------------|---------------|---------------|----------------|----------------|--------|
| no change, outdated timestamp | ✔️ | | | | | | | |
| no change, recent timestamp | ✔️ | | | | | | | |
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
| local edited, CRLF line endings | ✔️ | ✔️ | | | | | | |
| local edited, remote edited | ✔️ | ✔️ | | | ✔️ | | | |
| local edited, remote edited, same content | ✔️ | ✔️ | | | ✔️ | | | |
| local edited, remote edited, no common ancestor | ✔️ | ✔️ | | | ✔️ | | | |
| local edited, remote renamed | ✔️ | ✔️ | | | | ✔️ | | |
| local edited, remote edited, remote renamed | ✔️ | ✔️ | | | ✔️ | ✔️ | | |
| remote deleted | ✔️ | | | | | | ✔️ | |
| remote deleted, local edited | ✔️ | ✔️ | | | | | ✔️ | |
| stale file, incremental sync | ✔️ | | | | | | | ✔️ |
| stale file, full sync | ✔️ | | | | | | | ✔️ |
| stale file, remote edited, incremental sync | ✔️ | | | | ✔️ | | | ✔️ |
| stale file, remote edited, full sync | ✔️ | | | | ✔️ | | | ✔️ |
| stale file, local edited, incremental sync | ✔️ | ✔️ | | | | | | ✔️ |
| stale file, local edited, full sync | ✔️ | ✔️ | | | | | | ✔️ |
| stale file, local deleted | ✔️ | | | ✔️ | | | | ✔️ |
| stale file, local deleted, remote edited, incremental sync | ✔️ | | | ✔️ | ✔️ | | | ✔️ |
| stale file, local deleted, remote edited, full sync | ✔️ | | | ✔️ | ✔️ | | | ✔️ |
| local deleted | ✔️ | | | ✔️ | | | | |
| local deleted, remote edited | ✔️ | | | ✔️ | ✔️ | | | |
| local deleted, remote renamed | ✔️ | | | ✔️ | | ✔️ | | |
| local deleted, remote edited, remote renamed | ✔️ | | | ✔️ | ✔️ | ✔️ | | |
| local deleted, local edited, remote edited, remote renamed | ✔️ | ✔️ | | ✔️ | ✔️ | ✔️ | | |
| local deleted, remote deleted | ✔️ | | | ✔️ | | | ✔️ | |
| local renamed | ✔️ | | ✔️ | | | | | |
| local renamed, local edited | ✔️ | ✔️ | ✔️ | | | | | |
| local renamed, remote edited | ✔️ | | ✔️ | | ✔️ | | | |
| local renamed, local edited, remote edited | ✔️ | ✔️ | ✔️ | | ✔️ | | | |
| local renamed, remote renamed | ✔️ | | ✔️ | | | ✔️ | | |
| local renamed, local edited, remote renamed | ✔️ | ✔️ | ✔️ | | | ✔️ | | |
| local renamed, remote edited, remote renamed | ✔️ | | ✔️ | | ✔️ | ✔️ | | |
| local renamed, local edited, remote edited, remote renamed | ✔️ | ✔️ | ✔️ | | ✔️ | ✔️ | | |
| local renamed, remote deleted | ✔️ | | ✔️ | | | | ✔️ | |
| local renamed, local edited, remote deleted | ✔️ | ✔️ | ✔️ | | | | ✔️ | |
| local renamed, stale file | ✔️ | | ✔️ | | | | | ✔️ |
| local renamed, local edited, stale file | ✔️ | ✔️ | ✔️ | | | | | ✔️ |
| local renamed untracked, hash match | ✔️ | | ✔️ | | | | | |
| local renamed untracked, hash mismatch | ✔️ | ✔️ | ✔️ | | | | | |
| local renamed untracked, hash mismatch, remote edited | ✔️ | ✔️ | ✔️ | | ✔️ | | | |

### `sync_permissions.bats`

Test what happens when the user does not have the right permissions for the
notebook.

- **Permission** — user's access level on the target notebook
- **Notebook** — notebook exists and is accessible

| Test | Permission | Notebook |
|------|------------|----------|
| full sync switches to pull | viewer | ✔️ |
| pull, non-collaborator, public | none | ✔️ |
| pull, non-collaborator, private | none | ✔️ |
| pull, invalid token | invalid | ✔️ |
| pull, no token | none | ✔️ |
| pull, non-existent, owner | owner | ❌ |
| pull, non-existent, editor | editor | ❌ |
| pull, non-existent, viewer | viewer | ❌ |
| pull, non-existent, non-collaborator | none | ❌ |
| mid-sync, revoked, new file | editor | ✔️ |
| mid-sync, downgraded, new file | editor | ✔️ |
| mid-sync, revoked, local update | editor | ✔️ |
| mid-sync, downgraded, local update | editor | ✔️ |
| mid-sync, revoked, local rename | editor | ✔️ |
| mid-sync, downgraded, local rename | editor | ✔️ |
| mid-sync, revoked, local delete | editor | ✔️ |
| mid-sync, downgraded, local delete | editor | ✔️ |
| mid-sync, revoked, content update | editor | ✔️ |
| mid-sync, page deleted, content update | editor | ✔️ |
| mid-sync, page deleted, new file | editor | ✔️ |

### `sync_pagination.bats`

Ensure the script correctly fetches when there are more than `PAGE_SIZE` pages.

| Test |
|------|
| sync fetches all pages across pagination boundaries |
