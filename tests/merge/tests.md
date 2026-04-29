# Merge Tests

Three-way merge tests for `Page.three_way_merge`. Each test combines a client
operation (row) with a server operation (column), comparing the merge result
against expected output in `expected/{client}-{server}.md`.

The merge uses client-wins semantics: client changes are applied to the server
document. If patches fail, the result falls back to the client version entirely.


## Base Document

All operations start from this base (`inputs/base.md`):

```markdown
## Goblin

Small and cunning.

## Orc

Large and aggressive.
```


## Operations

Operations are organised by type. Some operations are used for both client and
server to test identical changes; others exist in pairs to test conflicts.

### No Change

- [unchanged](inputs/unchanged.md) — identical to base

### Additions

- [append-zombie](inputs/append-zombie.md) — add Zombie section at end (client)
- [append-wyvern](inputs/append-wyvern.md) — add Wyvern section at end (server)
- [prepend-aboleth](inputs/prepend-aboleth.md) — add Aboleth section at start (client)
- [prepend-banshee](inputs/prepend-banshee.md) — add Banshee section at start (server)
- [insert-ogre](inputs/insert-ogre.md) — add Ogre section in middle (client)
- [insert-naga](inputs/insert-naga.md) — add Naga section in middle (server)

### Edits

- [edit-goblin-sneaky](inputs/edit-goblin-sneaky.md) — change "cunning" to "sneaky" (client)
- [edit-goblin-stupid](inputs/edit-goblin-stupid.md) — change "cunning" to "stupid" (server)
- [edit-orc](inputs/edit-orc.md) — add ", and territorial" to Orc (both)

### Deletions

- [delete-goblin](inputs/delete-goblin.md) — remove Goblin section (both)
- [delete-orc](inputs/delete-orc.md) — remove Orc section (both)

### Replacements

- [goblin-to-ghoul](inputs/goblin-to-ghoul.md) — replace Goblin with Ghoul (client)
- [goblin-to-gargoyle](inputs/goblin-to-gargoyle.md) — replace Goblin with Gargoyle (server)
- [all-dragons](inputs/all-dragons.md) — replace entire document with dragons (client)
- [all-fey](inputs/all-fey.md) — replace entire document with fey (server)


## Matrix

Rows are client inputs, columns are server inputs.

Cells marked ✗ indicate that `git merge-file` is unable to merge this
combination.

| client ↓ server →      | unchanged | append-wyvern | prepend-banshee | insert-naga | edit-goblin-stupid | edit-orc | delete-goblin | delete-orc | goblin-to-gargoyle | all-fey |
|------------------------|-----------|---------------|-----------------|-------------|--------------------|---------:|---------------|------------|--------------------|---------|
| **unchanged**          |           |               |                 |             |                    |          |               |            |                    |         |
| **append-zombie**      |           |               |                 |             |                    |        ✗ |               |          ✗ |                    |       ✗ |
| **prepend-aboleth**    |           |               |               ✗ |             |                    |          |             ✗ |            |                  ✗ |       ✗ |
| **insert-ogre**        |           |               |                 |           ✗ |                    |          |               |            |                    |         |
| **edit-goblin-sneaky** |           |               |                 |             |                    |          |               |          ✗ |                    |         |
| **edit-orc**           |           |             ✗ |                 |             |                    |        ✗ |               |            |                    |         |
| **delete-goblin**      |           |               |               ✗ |           ✗ |                    |          |               |          ✗ |                    |         |
| **delete-orc**         |           |             ✗ |                 |           ✗ |                  ✗ |        ✗ |             ✗ |            |                  ✗ |         |
| **goblin-to-ghoul**    |           |               |               ✗ |             |                    |          |               |          ✗ |                    |         |
| **all-dragons**        |           |             ✗ |               ✗ |           ✗ |                    |        ✗ |               |            |                    |         |
