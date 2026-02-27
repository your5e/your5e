# Notebook Sync

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
4.  Update the local cache to reflect this.
5.  _GET_ remote state of the notebook.
6.  _GET_ any files different to the local cache.
7.  _rm_ any files deleted remotely (any local edits will have already
    un-deleted them in step 2).
8.  Cache the state.

If any HTTP request during sync fails, the sync should be abandoned and
retried later.
