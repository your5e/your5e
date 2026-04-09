@after ../api/sync.md
@queue

Reimplement the sync-notebook script in Typescript, so it can be tested
independently.

- [X] reimplement the first sync tests
        - include linting
        - include line length tests
- [X] integrate into CI

- [X] reimplement the subsequent sync tests
- [X] reimplement the permissions tests
- [X] reimplement the pagination tests
- [ ] pull using updates-since

Using Node or Electron APIs means the plugin can't work on mobile.

- [ ] refactor to use Obsidian APIs instead of Node.js
        - replace NodeFileSystem with ObsidianFileSystem using app.vault APIs
        - replace node:crypto SHA-256 with cross-platform alternative
        - replace node:path with Obsidian or cross-platform path utilities

- [ ] update the sync engine to debounce local changes and then push after
      timeout
- [ ] successful push also triggers pull
