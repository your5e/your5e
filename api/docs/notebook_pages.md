# Notebook Pages

Operations on individual pages within a notebook.


## POST `/api/notebooks/{username}/{notebook-slug}/`

Create a new page in the notebook. Accepts a multipart form with:

- `file` (required): the file content to upload
- `filename` (optional): override the uploaded file's name

If `filename` is not provided, the uploaded file's original name is used.
Filenames must have a file extension. Filenames can include directories
(e.g. `heroes/Theron.md`). Hidden files (names starting with `.`) are not
allowed.

### Response

```json
{
  "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "url": "/api/notebooks/norm/campaign-notes/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "html_url": "https://your5e.com/notebooks/norm/campaign-notes/new-page",
  "filename": "New Page.md",
  "mime_type": "text/markdown",
  "version": 1,
  "created_by": "norm",
  "updated_at": "2024-01-15T12:00:00Z",
  "content_hash": "a1b2c3..."
}
```

Returns _201 Created_ on success.

Returns _400 Bad Request_ if:
- no file is provided
- the filename has no file extension
- the filename is a hidden file (starts with `.`)
- the path would be nested under an existing file

Returns _409 Conflict_ if a page with the same path already exists.


## GET `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Returns the current content of a page, with the appropriate `Content-Type`
header.

Arguments:

- `version` returns a specific version of the page instead of the latest


## PATCH `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Update a page's metadata. Either rename a page or revert it to an older
version. A new version is created with the change. Provide exactly one of
`filename` or `revert_to`.

### Renaming a page

```json
{
  "filename": "New Name.md"
}
```

The content is preserved. If the filename is unchanged, no new version is
created. Filenames can include directories (e.g. `heroes/Theron.md`). Hidden
files (names starting with `.`) are not allowed.

### Reverting to an older version

```json
{
  "revert_to": 2
}
```

Creates a new version with the content, filename, and mime type from the
specified version number. If the page is already at that content and filename,
no new version is created.

### Response

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

Returns _400 Bad Request_ if:
- neither `filename` nor `revert_to` is provided
- both `filename` and `revert_to` are provided
- the filename contains forbidden characters
- the filename is a hidden file (starts with `.`)
- the filename conflicts with an existing page
- the path would be nested under an existing file
- the version number does not exist


## PUT `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Update the content of a page, creating a new version. The request body
should be the raw content, with the appropriate `Content-Type` header.
If the page has been soft-deleted, this will restore it.

The response structure is the same as PATCH, with an additional
`previous_hash` field containing the content hash before this update,
which can be used for client-side conflict detection.


## DELETE `/api/notebooks/{username}/{notebook-slug}/{uuid}`

Soft-delete a page. The page can be restored by updating its content with PUT.

Returns _204 No Content_ on success.
