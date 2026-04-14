@after plugin.md

Community plugin submission requires a standalone GitHub repository.
Use `git subtree` to publish the plugin directory to a separate repo:

```bash
git subtree push --prefix=obsidian-plugin plugin-origin main
```

- [ ] submit to Obsidian community plugins repository for automatic
      distribution
