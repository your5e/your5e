# Your 5E

Tools for running your 5th edition adjacent roleplaying games.


## Development

Development is done with docker, spinning up the stack is:

```
# makes the site available at http://localhost:5843/
(computer)% make dev

# and in another terminal...
(computer)% make test
```

Test data includes [a map](users/management/commands/random-hexmap-7.png) by
[Dyson Logos](https://dysonlogos.blog/2025/02/07/the-autumn-lands-hex-map-g/).

The integration tests ([first_sync.bats](tests/first_sync.bats),
[subsequent_sync.bats](tests/subsequent_sync.bats)) serve as both tests of the
API, and as a reference implentation of how I think notebook sync should work.
What possible scenarios can happen, and how to handle them. Happily, it also
happens to implement a full sync bash script if you need to sync a directory.
