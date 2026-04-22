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
- [X] pull using updates-since


# Error reporting @phase

When sync fails due to network or API errors (5xx), the plugin should
notify the user via Obsidian's notification system.

- [ ] sync engine reports failure to the plugin when network/API errors occur
- [ ] plugin displays notification bubble on sync failure

Unresolvable conflicts (hidden files, missing extension) should be reported
once per session, not every sync cycle. Track reported paths in a plugin
instance variable (cleared on restart).

- [ ] track reported unresolvable conflicts in plugin instance variable
- [ ] report unresolvable conflict only once per plugin lifetime


# Obsidian API @phase

Using Node or Electron APIs means the plugin can't work on mobile.

- [ ] refactor to use Obsidian APIs instead of Node.js
        - replace NodeFileSystem with ObsidianFileSystem using app.vault APIs
        - replace node:crypto SHA-256 with cross-platform alternative
        - replace node:path with Obsidian or cross-platform path utilities

- [ ] update the sync engine to debounce local changes and then push after
      timeout
- [ ] successful push also triggers pull

And let's neaten things while we're at it.

- [ ] decide if sync messages end in period or not, stick to one style
