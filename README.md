# Your 5E

Tools for running your 5th edition adjacent roleplaying games.


## Development

Development is done with docker, spinning up the stack is:

```
# install prerequisites
(computer)% brew install bats-core shellcheck node

# install npm dependencies for Obsidian plugin development
(computer)% make setup-obsidian-plugin

# reset the development database
(computer)% make reset

# make the site available at http://localhost:5843/
(computer)% make dev

# run all tests (requires test server)
(computer)% make server-tests
(computer)% make test

# or run individual test suites
(computer)% make test-django
(computer)% make test-sync-integration
(computer)% make test-obsidian-plugin

# update archival/testing screenshots
(computer)% make scry

# update the Obsidian plugin in test vault during development
(computer)% make debug-plugin

# build the Obsidian plugin
(computer)% make build-obsidian-plugin

# shut down the test server when done
(computer)% make server-tests-down
```

Test data includes [a map](users/management/commands/random-hexmap-7.png) by
[Dyson Logos](https://dysonlogos.blog/2025/02/07/the-autumn-lands-hex-map-g/).

The integration tests `tests/*.bats` serve as both tests of the API, and as a
reference implementation of how I think notebook sync should work. What possible
scenarios can happen, and how to handle them. Happily, it also happens to
implement a full sync bash script if you need to sync a directory.

```
(computer)% export YOUR5E_API_TOKEN='abcdefg...'

# one-time sync
(computer)% tests/sync-notebook.sh user/notebook dir

# monitor and poll for changes
(computer)% tests/sync-notebook.sh -w user/notebook dir
```


## Importing Public Notebooks

System notebooks (owned by `your5e`) are populated using the `import_notebook`
management command. _The notebook must already exist._

```
(computer)% docker compose exec web python manage.py import_notebook \
    /path/to/folder notebook-slug
```
