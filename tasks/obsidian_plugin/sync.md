@after ../api/notebook.md

An Obsidian plugin to sync a folder in a Vault with a Campaign Notebook.


# Configuration @phase

The plugin can sync multiple folders. Each folder would require:
- API endpoint base (defaults to your5e, can be overridden)
- auth token
- folder
- notebook slug
- update poll time (0 for manual sync only)

- [ ] provide configuration
- [ ] prove multiple sync folders can be added with different
      endpoints and tokens
- [ ] prove plugin still has config after reload


# Sync pull @phase

Implement the pull part of sync. Push requires a testing API, so start here.

- [ ] implement button to trigger sync
        - with no stored state, fetch entire state of notebook
        - with stored state, fetches only updates-since
        - ensure stored state without server changes merges and does not
          overwrite state with nothing (triggering initial sync again)
- [ ] process sync state
        - compare list of remote files with local
        - pull any files that are different
        - delete any files that have been deleted/are missing
- [ ] prove local changes are overwritten by the pull
        - at least one file should remain untouched
        - at least one file should change
        - at least one file should be renamed
        - at least one file should be deleted
- [ ] prove that updates are localised to that folder only
        - path is relative to folder, does not escape
- [ ] prove that local changes are not overwritten on subsequent sync
- [ ] prove that sync is called on startup
- [ ] prove that sync is called intermittently
- [ ] prove that server hashes and local hashes match
- [ ] prove that no response/network failure does not trash the local state


# Sync push @phase

Implement the push part of sync. By pushing changes before pulling, local
changes take precedence if it has been a while between syncs. This should be
fine as the server doesn't hard delete pages and keeps versions, so any local
unwanted changes should be recoverable.

- [ ] ensure plugin determines if token allows pushing before attempt, editors
      can be demoted to viewers, and vice-versa
- [ ] before pulling, push any files that are different
        - compare list of remote files with local
        - delete missing files
        - update changed and renamed files
        - mark anything changed as resolved
        - process pull for anything left unresolved
- [ ] prove that local changes temporarily unable to be pushed interrupts the
      sync, so pull doesn't overwrite local
- [ ] prove when read-only viewer sync, local changes are overwritten if the remote
      changes (that is the point of viewer sync)
- [ ] properly consider multi-device pushing with long offline periods,
      ensure files do not flip-flop back to old versions


# File watcher @phase

Implement the file watcher.

- [ ] watch configured folders for changes
- [ ] prove updates outside of watched folders are ignored
- [ ] prove updates inside of watched folders are attached to the
      correct folder configuration
- [ ] debounce updates
        - reset a file-specific timer when a file is updated
        - when timer expires, log pushing an update
        - prove that multiple updates in short succession only trigger
          one log message
- [ ] prove that sync firing after local edits but before timer pushes changes
      even if remote has also changed the file (most recent edit wins)
- [ ] prove timer triggers sync
