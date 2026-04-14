@after sync_engine.md
@queue

An Obsidian plugin to sync a folder in a Vault with a Campaign Notebook.
Configuration allows general base URL and API token, but can be overridden
per folder. Per-folder config is vault folder, notebook ID (and overrides).

- [X] create plugin using sync_engine
        - configuration settings
        - syncs once per minute for testing

- [X] do not sync when editing config
- [ ] prove each folder has its own state
- [X] sync each folder on a different irregular interval around 10 minutes,
      to avoid swamping the server with multiple notebooks configured
- [ ] prove updates to files outside of the target folder do not trigger
      sync unnecessarily
- [X] initial sync on launch should also not swamp the server

- [ ] add 'sync now' to command palette
- [ ] add 'show sync log' to command palette
- [ ] add 'show sync log' for the ribbon, but not on by default
- [ ] add sync status to statusbar, context menu includes opening the log

Community plugin submission requires a standalone GitHub repository.
Use `git subtree` to publish the plugin directory to a separate repo:

```bash
git subtree push --prefix=obsidian-plugin plugin-origin main
```

- [ ] submit to Obsidian community plugins repository for automatic
      distribution
