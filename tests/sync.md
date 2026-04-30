# Notebook Sync

This document specifies the sync algorithm. The reference implementation is in
`sync-notebook.sh`. The BATS test files contain scenarios that any sync
client should handle — use them to verify your implementation.

The one-line summary: aim to preserve content at all times, ideally on the
server, locally if there is no ability to write to the notebook.

The server both keeps deleted files for a while and keeps previous versions of
files, so pushing old changes is never wholly destructive.

Concurrent edits should be merged into the file when possible, and secondary
files created when changes conflict. This means the user needs to reconcile,
but nothing should be thrown away. Local changes are never deleted.

Broadly, the algorithm to sync the local directory is:

1.  _GET_ remote state of the notebook.
2.  Scan for untracked renames (files moved locally outside of sync)
    by matching missing tracked files to untracked files by content hash.
3.  Check for stale files (UUIDs in cache but not on remote). If a stale
    file has local changes, preserve it in a conflict file.
4.  _PATCH_ locally renamed files (cached filename differs from server filename).
5.  _DELETE_ any deleted files (in the cache, no longer in the directory).
6.  _POST_ new local files (not in the cache).
7.  _PUT_ changed local files (differ from the cache). The server will merge
    or replace if the previous version differs from the cached hash. If the
    returned hash differs from the local file (server merged or normalised
    line endings), _GET_ the updated content.
8.  _rm_ any files deleted remotely. If the file has local changes, rename
    it to a conflict file first.
9.  _mv_ any files where the remote UUID now has a different filename.
10. _GET_ any files where the local hash differs from the server's hash
    (remote updates). If a local file at this path has changes, attempt a
    three-way merge; if merging fails, rename the local file to a conflict
    file and fetch the remote content.

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

- **Tracked** — file is in the local state from previous sync
- **Local Edited** — local content differs from cached hash
- **Local Renamed** — local file has been moved to a different path
- **Local Deleted** — local file no longer exists
- **Remote Edited** — server content hash differs from cached
- **Remote Renamed** — server filename differs from cached
- **Remote Deleted** — server has soft-deleted the file
- **Stale** — tracked UUID no longer exists on server
- **Aware** — sync state knows about local deletion
- **Mergeable** — concurrent edits can be three-way merged

| Test | Tracked | Local Edited | Local Renamed | Local Deleted | Remote Edited | Remote Renamed | Remote Deleted | Stale | Aware | Mergeable |
|------|---------|--------------|---------------|---------------|---------------|----------------|----------------|-------|-------|-----------|
| no change, outdated timestamp | ✔️ | | | | | | | | | |
| no change, recent timestamp | ✔️ | | | | | | | | | |
| untracked file | | | | | | | | | | |
| untracked file, local edited, directory | | ✔️ | | | | | | | | |
| untracked file, local edited | | ✔️ | | | | | | | | |
| untracked file, remote renamed | | | | | | ✔️ | | | | |
| untracked file, local edited, remote renamed | | ✔️ | | | | ✔️ | | | | |
| remote edited | ✔️ | | | | ✔️ | | | | | |
| remote renamed | ✔️ | | | | | ✔️ | | | | |
| remote renamed, local edited, directory | ✔️ | ✔️ | | | | ✔️ | | | | |
| remote edited, remote renamed | ✔️ | | | | ✔️ | ✔️ | | | | |
| remote renamed, swapped | ✔️ | | | | | ✔️ | | | | |
| remote renamed, chain | ✔️ | | | | | ✔️ | | | | |
| remote renamed, chain reversed | ✔️ | | | | | ✔️ | | | | |
| remote renamed, cycle | ✔️ | | | | | ✔️ | | | | |
| remote renamed, cycle, local edited, mergeable | ✔️ | ✔️ | | | | ✔️ | | | | ✔️ |
| remote renamed, cycle, local edited, unmergeable | ✔️ | ✔️ | | | | ✔️ | | | | ❌ |
| remote renamed, cycle, untracked file | ✔️ | | | | | ✔️ | | | | |
| local edited | ✔️ | ✔️ | | | | | | | | |
| local edited, CRLF line endings | ✔️ | ✔️ | | | | | | | | |
| local edited, remote edited, mergeable | ✔️ | ✔️ | | | ✔️ | | | | | ✔️ |
| local edited, remote edited, unmergeable | ✔️ | ✔️ | | | ✔️ | | | | | ❌ |
| local edited, remote edited, same content | ✔️ | ✔️ | | | ✔️ | | | | | |
| local edited, remote edited, no common ancestor | ✔️ | ✔️ | | | ✔️ | | | | | |
| local edited, remote renamed | ✔️ | ✔️ | | | | ✔️ | | | | |
| local edited, remote edited, remote renamed, mergeable | ✔️ | ✔️ | | | ✔️ | ✔️ | | | | ✔️ |
| local edited, remote edited, remote renamed, unmergeable | ✔️ | ✔️ | | | ✔️ | ✔️ | | | | ❌ |
| remote deleted | ✔️ | | | | | | ✔️ | | | |
| remote deleted, local edited | ✔️ | ✔️ | | | | | ✔️ | | | |
| stale file, incremental sync | ✔️ | | | | | | | ✔️ | | |
| stale file, full sync | ✔️ | | | | | | | ✔️ | | |
| stale file, remote edited, incremental sync | ✔️ | | | | ✔️ | | | ✔️ | | |
| stale file, remote edited, full sync | ✔️ | | | | ✔️ | | | ✔️ | | |
| stale file, local edited, incremental sync | ✔️ | ✔️ | | | | | | ✔️ | | |
| stale file, local edited, full sync | ✔️ | ✔️ | | | | | | ✔️ | | |
| stale file, local edited, remote edited, incremental sync | ✔️ | ✔️ | | | ✔️ | | | ✔️ | | |
| stale file, local edited, remote edited, full sync | ✔️ | ✔️ | | | ✔️ | | | ✔️ | | |
| stale file, local deleted | ✔️ | | | ✔️ | | | | ✔️ | | |
| stale file, local deleted, remote edited, incremental sync | ✔️ | | | ✔️ | ✔️ | | | ✔️ | | |
| stale file, local deleted, remote edited, full sync | ✔️ | | | ✔️ | ✔️ | | | ✔️ | | |
| local deleted, aware | ✔️ | | | ✔️ | | | | | ✔️ | |
| local deleted, unaware | ✔️ | | | ✔️ | | | | | ❌ | |
| local deleted, remote edited | ✔️ | | | ✔️ | ✔️ | | | | | |
| local deleted, remote renamed | ✔️ | | | ✔️ | | ✔️ | | | | |
| local deleted, remote edited, remote renamed | ✔️ | | | ✔️ | ✔️ | ✔️ | | | | |
| local deleted, aware, local edited, remote edited | ✔️ | ✔️ | | ✔️ | ✔️ | | | | ✔️ | |
| local deleted, unaware, local edited, remote edited | ✔️ | ✔️ | | ✔️ | ✔️ | | | | ❌ | |
| local deleted, aware, local edited, remote edited, remote renamed | ✔️ | ✔️ | | ✔️ | ✔️ | ✔️ | | | ✔️ | |
| local deleted, unaware, local edited, remote edited, remote renamed | ✔️ | ✔️ | | ✔️ | ✔️ | ✔️ | | | ❌ | |
| local deleted, remote deleted | ✔️ | | | ✔️ | | | ✔️ | | | |
| local renamed, aware | ✔️ | | ✔️ | | | | | | ✔️ | |
| local renamed, aware, local edited | ✔️ | ✔️ | ✔️ | | | | | | ✔️ | |
| local renamed, aware, remote edited | ✔️ | | ✔️ | | ✔️ | | | | ✔️ | |
| local renamed, aware, local edited, remote edited, mergeable | ✔️ | ✔️ | ✔️ | | ✔️ | | | | ✔️ | ✔️ |
| local renamed, aware, local edited, remote edited, unmergeable | ✔️ | ✔️ | ✔️ | | ✔️ | | | | ✔️ | ❌ |
| local renamed, aware, remote renamed | ✔️ | | ✔️ | | | ✔️ | | | ✔️ | |
| local renamed, aware, local edited, remote renamed | ✔️ | ✔️ | ✔️ | | | ✔️ | | | ✔️ | |
| local renamed, aware, remote edited, remote renamed | ✔️ | | ✔️ | | ✔️ | ✔️ | | | ✔️ | |
| local renamed, aware, local edited, remote edited, remote renamed, mergeable | ✔️ | ✔️ | ✔️ | | ✔️ | ✔️ | | | ✔️ | ✔️ |
| local renamed, aware, local edited, remote edited, remote renamed, unmergeable | ✔️ | ✔️ | ✔️ | | ✔️ | ✔️ | | | ✔️ | ❌ |
| local renamed, aware, remote deleted | ✔️ | | ✔️ | | | | ✔️ | | ✔️ | |
| local renamed, aware, local edited, remote deleted | ✔️ | ✔️ | ✔️ | | | | ✔️ | | ✔️ | |
| local renamed, aware, stale file | ✔️ | | ✔️ | | | | | ✔️ | ✔️ | |
| local renamed, aware, local edited, stale file | ✔️ | ✔️ | ✔️ | | | | | ✔️ | ✔️ | |
| local renamed, unaware, hash match | ✔️ | | ✔️ | | | | | | ❌ | |
| local renamed, unaware, hash mismatch | ✔️ | ✔️ | ✔️ | | | | | | ❌ | |
| local renamed, unaware, hash mismatch, remote edited | ✔️ | ✔️ | ✔️ | | ✔️ | | | | ❌ | |
| conflict hostname exists | | ✔️ | | | | | | | | |
| conflict hostname exists, conflict date exists | | ✔️ | | | | | | | | |

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

### `combined_sync.bats`

Test that repeated syncs do not break in unexpected ways. Each test makes one
change and syncs, building on the state from the previous test.

| Test |
|------|
| initial sync |
| stable sync |
| local edit |
| server edit |
| merged edit |
| replaced edit |
| conflicting new file |
| local rename, aware |
| server delete |
| server rename |
| local rename, unaware |
| local delete, aware |
| local delete, unaware |
| stale file |
| stale file, full sync |
| final stable state |
| final stable sync |
