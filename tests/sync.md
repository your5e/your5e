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
