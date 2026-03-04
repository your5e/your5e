@after notebook.md

Proof-of-concept sync script for notebooks.
See [the algorithm](../../tests/sync.md).

- [X] create download-only sync script
        - integration tests against dev seed
- [X] don't request unchanged files
        - cache sync state and compare hashes
- [X] ensure rename cycles are broken
- [ ] implement full two-way sync
