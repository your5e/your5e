# Notebook Pages

Operations on individual pages within a notebook.


## GET `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Returns the current content of a page, with the appropriate `Content-Type`
header.

Arguments:

- `version` returns a specific version of the page instead of the latest


## PATCH `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Rename a page by updating its filename. The content is preserved and a new
version is created. If the filename is unchanged, no new version is created.

Request body (JSON):

```json
{
  "filename": "New Name.md"
}
```

The response structure is:

```json
{
  "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "url": "/api/notebooks/norm/campaign-notes/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "html_url": "https://your5e.com/notebooks/norm/campaign-notes/new-name",
  "filename": "New Name.md",
  "mime_type": "text/markdown",
  "version": 2,
  "created_by": "norm",
  "updated_at": "2024-01-15T12:00:00Z",
  "content_hash": "a1b2c3..."
}
```

Filenames can include directories (e.g. `heroes/Theron.md`).

Returns _400 Bad Request_ if:
- the filename is missing
- the filename contains forbidden characters
- the filename conflicts with an existing page


## PUT `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Update the content of a page, creating a new version. The request body
should be the raw content, with the appropriate `Content-Type` header.
If the page has been soft-deleted, this will restore it.

The response structure is the same as PATCH, with an additional
`previous_hash` field containing the content hash before this update,
which can be used for client-side conflict detection.
