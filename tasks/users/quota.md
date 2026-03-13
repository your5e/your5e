@after ../wikis/model.md
@queue

Per-user storage quota to limit total content size across all notebooks.

User model fields:
- `notebook_quota` — maximum allowed, default 50MB
- `notebook_used` — running total

Accounting:
- incremented when a new version is created, by the size of its content
- decremented when a purge removes content
- duplicating a system notebook is free
- edits by collaborators count against the notebook owner's quota

Enforcement:
- no new versions or pages when over quota
- reads, viewing history always allowed
- applies uniformly to all content types (text, images, maps)

- [ ] measure storage quota
        - quota editable in admin, usage read-only
        - quota and usage shown in user profile
        - quota and usage available via API
- [ ] enforce storage quota
        - disable editing/creation controls
        - error message on update attempts
        - error response in API includes quota info
