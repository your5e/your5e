# Notebooks

List notebooks you have access to.

All endpoints are cursor-paginated, ordered by most recently updated. Use the
`next` and `previous` links in the response to navigate between pages.

The response structure is:

```json
{
  "next": "/api/notebooks/?cursor=...",
  "previous": null,
  "results": [
    {
      "name": "Campaign Notes",
      "slug": "campaign-notes",
      "owner": "norm",
      "visibility": "public",
      "url": "/notebooks/norm/campaign-notes/",
      "last_updated": "2024-01-15T10:30:00Z",
      "copied_from": null
    },
    {
      ...
    }
  ],
  "total_results": 42
}
```

## GET /api/notebooks

Lists all notebooks you have access to:

- yours
- those directly shared with you, either as an editor or viewer
- those shared to all users
- public notebooks


## GET /api/notebooks/public

Lists all public notebooks.


## GET /api/notebooks/internal

Lists all notebooks shared to all users but not public.


## GET /api/notebooks/private

Lists all private notebooks, either that you own or directly shared with you. .


## GET /api/notebooks/{username}/

Lists notebooks owned by that user that you have access to.

Returns `404 Not Found` if the username does not exist.
