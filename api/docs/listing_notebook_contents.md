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
  "results": [
    {
      "id": 123,
      "path": "session-one",
      "filename": "Session One.md",
      "mime_type": "text/markdown",
      "version": 3,
      "created_by": "norm",
      "updated_at": "2024-01-15T10:30:00Z",
      "deleted_at": null
    },
    {
      "id": 456,
      "path": "old-draft",
      "filename": "old-draft.md",
      "mime_type": "text/markdown",
      "version": 1,
      "created_by": "norm",
      "updated_at": null,
      "deleted_at": "2024-01-15T08:00:00Z"
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
