# Your 5E

Tools for running your 5th edition adjacent roleplaying games.


## Development

Development is done with docker, spinning up the stack is:

```
# reset the development database
(computer)% make reset

# make the server for running integration tests available
(computer)% make test-server
(computer)% make test-integration
...
(computer)% make test-server-down

# make the site available at http://localhost:5843/
(computer)% make dev
```

Test data includes [a map](users/management/commands/random-hexmap-7.png) by
[Dyson Logos](https://dysonlogos.blog/2025/02/07/the-autumn-lands-hex-map-g/).

The integration tests `tests/*.bats` serve as both tests of the API, and as a
reference implentation of how I think notebook sync should work. What possible
scenarios can happen, and how to handle them. Happily, it also happens to
implement a full sync bash script if you need to sync a directory.
