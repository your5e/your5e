@after sync_engine.md
@queue

An Obsidian plugin to sync a folder in a Vault with a Campaign Notebook.
Configuration allows general base URL and API token, but can be overridden
per folder. Per-folder config is vault folder, notebook ID (and overrides).

- [X] create plugin using sync_engine
        - configuration settings
        - syncs once per minute for testing

- [X] do not sync when editing config
- [X] prove each folder has its own state
- [X] sync each folder on a different irregular interval around 10 minutes,
      to avoid swamping the server with multiple notebooks configured
- [X] initial sync on launch should also not swamp the server
- [X] save button for new folder, folds section and triggers sync
- [X] {re,}start the scheduler on settings change, not only on plugin load
- [ ] removing a folder mapping should remove its state
- [ ] build to a permanent artifact zip file, not an emphemeral zip on the
      docker image

Push updates more readily than waiting for sync.

- [ ] watch for changes, debounce, push after 3 minutes of inactivity
        - prove updates trigger sync outside of the normal window, and reset
          the sync timer
        - prove updates to files outside of the target folder do not trigger

Add more control and observability to sync.

- [ ] add 'sync now' to command palette
- [ ] add 'show sync log' to command palette
- [ ] add 'show sync log' for the ribbon, but not on by default
- [ ] add sync status to statusbar, context menu includes opening the log
- [ ] add debug mode setting
