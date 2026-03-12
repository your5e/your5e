@after notebook.md

Proof-of-concept sync script for notebooks.
See [the algorithm](../../tests/sync.md).

While the API is read-only, we can implement only some of the algorithm.

- [X] create download-only sync script
        - integration tests against dev seed
- [X] don't request unchanged files
        - cache sync state and compare hashes
- [X] ensure rename cycles are broken

Once the API is read-write, we can implement the rest of the algorithm.

- [X] make the existing tests exercise pull-only mode
- [X] improve test readability with semantic helpers
- [X] mirror the existing pull tests for push
- [X] add any push-specific tests missing from the matrix
- [X] implement user permission scenarios
- [ ] ensure results pagination
- [ ] cover any remaining API error scenarios

We could also make the script a watcher to push updates real-time.

- [ ] update the script to watch for changes
        - debounce changes before pushing, many small edits in quick
          succession should be coalesced
        - renames happen immediately
        - sync on an interval to fetch remote changes
        - recovering from abandoned sync, still pushes local changes
