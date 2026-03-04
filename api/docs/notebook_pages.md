# Notebook Pages

Operations on individual pages within a notebook.


## GET `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Returns the current content of a page, with the appropriate `Content-Type`
header.

Arguments:

- `version` returns a specific version of the page instead of the latest


## PUT `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Update the content of a page, creating a new version. The request body
should be the raw content, with the appropriate `Content-Type` header.
If the page has been soft-deleted, this will restore it.

The response structure is:

```json
{
  "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "path": "session-one",
  "filename": "Session One.md",
  "mime_type": "text/markdown",
  "version": 4,
  "created_by": "norm",
  "updated_at": "2024-01-15T12:00:00Z",
  "content_hash": "b2c3d4...",
  "previous_hash": "a1b2c3..."
}
```

The `previous_hash` is the content hash before this update, which can be
used for client-side conflict detection.
