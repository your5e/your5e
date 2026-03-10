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
- [ ] implement push sync tests
- [ ] implement user permission scenarios
- [ ] ensure results pagination
- [ ] add extra API error scenarios
