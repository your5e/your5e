# Listing Notebooks

List notebooks you have access to.

All endpoints are cursor-paginated, ordered by most recently updated. Use the
`next` and `previous` links in the response to navigate between pages.

The response structure is:

```json
{
  "next": "/v1/notebooks/?cursor=...",
  "previous": null,
  "results": [
    {
      "name": "Campaign Notes",
      "slug": "campaign-notes",
      "owner": "norm",
      "visibility": "public",
      "url": "/v1/notebooks/norm/campaign-notes/",
      "html_url": "https://your5e.com/notebooks/norm/campaign-notes/",
      "last_updated": "2024-01-15T10:30:00.123456Z",
      "copied_from": null,
      "editable": true
    },
    {
      ...
    }
  ],
  "total_results": 42
}
```

Arguments:

- `cursor` used when paginating results (links to prev/next results are
  included in the response)


## GET `/v1/notebooks`

Lists all notebooks you have access to:

- yours
- those directly shared with you, either as an editor or viewer
- those shared to all users
- public notebooks


## GET `/v1/notebooks/public`

Lists all public notebooks.


## GET `/v1/notebooks/internal`

Lists all notebooks shared to all users but not public.


## GET `/v1/notebooks/private`

Lists all private notebooks, either that you own or are directly shared with
you.


## GET `/v1/notebooks/{username}/`

Lists notebooks owned by that user that you have access to.

Returns _404 Not Found_ if the user does not exist.
