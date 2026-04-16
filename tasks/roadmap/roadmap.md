Generate a user-facing roadmap help page from our task files.

A roadmap entry is another task file, `tasks/roadmap/big-feature.md`, which
defers to the actual work:

```markdown
# Big Feature

Explanation about the feature.

- [ ] First public stage of feature       @after ../big/alpha.md
- [ ] Second public stage of feature      @after ../big/refine.md @after../big/bugs.md
- [ ] General availability                @after ../big/
```

Each item gets it status from the amount of work done in the immediate
dependencies:

- **Planned** — zero tasks marked complete
- **In Progress** — at least one task marked complete
- **Available** — the _roadmap_ task is marked complete

The roadmap task itself stands as a reminder to test the feature thoroughly
once deployed before declaring it available.


- [ ] create `help/roadmap.py` to parse task files
        - state is properly calculated
        - sort available before in progress before planned, then alphabetical
- [ ] generate the markdown document from the roadmap data
- [ ] integrate into `sync_docs`, making that an automatic part of deployment
