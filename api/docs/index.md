# API

All API endpoints require [[Authentication]].

## Error Responses

All error responses are returned as JSON with a single `error` key:

```json
{"error": "Description of what went wrong."}
```

Common errors:

- `401 Unauthorised` - authentication required or token invalid
- `403 Forbidden` - you don't have permission to perform this action
- `404 Not Found` - the resource doesn't exist or isn't visible to you

## Auth / Debugging

- [[Ping]] - test your authentication works

## Notebooks

- [[Listing Notebooks]] - find out which notebooks you have access to
- [[Listing Notebook Contents]] - find out what pages are in the notebook
- [[Notebook Pages]] - read and update page content
