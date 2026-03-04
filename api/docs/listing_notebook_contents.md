# Listing Notebook Contents

List pages in a notebook. The content of the pages are not returned, only the
metadata.

The endpoint is cursor-paginated, ordered by most recently updated. Use the
`next` and `previous` links in the response to navigate between pages.

Pages that have been deleted but not yet purged return `deleted_at`
instead of `updated_at`.

## GET `/api/notebooks/{username}/{notebook-slug}/`

The response structure is:

```json
{
  "next": null,
  "previous": null,
  "editable": true,
  "results": [
    {
      "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "path": "session-one",
      "filename": "Session One.md",
      "mime_type": "text/markdown",
      "version": 3,
      "created_by": "norm",
      "updated_at": "2024-01-15T10:30:00Z",
      "deleted_at": null,
      "content_hash": "a1b2c3..."
    },
    {
      "uuid": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "path": "old-draft",
      "filename": "old-draft.md",
      "mime_type": "text/markdown",
      "version": 1,
      "created_by": "norm",
      "updated_at": null,
      "deleted_at": "2024-01-15T08:00:00Z",
      "content_hash": "d4e5f6..."
    },
    {
      ...
    }
  ],
  "total_results": 8
}
```

Arguments:

- `since` shows only those pages updated or deleted since _timestamp_,
  which can be either ISO 8601 (`?since=2024-01-15T10:30:00Z`) or epoch
  seconds (`?since=1705312200`)
- `cursor` used when paginating results (links to prev/next results are
  included in the response)


## GET `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Returns the current content of a page, with the appropriate `Content-Type`
header.

Arguments:

- `version` returns a specific version of the page instead of the latest
