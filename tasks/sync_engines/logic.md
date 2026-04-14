Logic changes that affect both the bash `tests/sync-notebook.sh` and
TypeScript `obsidian-plugin/src` sync engines.

The test matrix is `tests/sync.md` and should stay in sync between both
engines.

# rewrite sync tests

The current tests rewind the _local_ state to _simulate_ server changes.
We should actually be mutating the server state instead, so we can properly
test the incremental sync in all of the scenarios.

- [ ] rewrite the setup helpers for the BATS tests
- [ ] rewrite the setup helpers for the Obsidian tests
