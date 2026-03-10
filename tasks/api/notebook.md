@after api.md ../notebooks/model.md

REST endpoints for Notebooks.

# notebooks listing @phase

- [X] api/notebooks/
        - GET returns all notebooks you have access to, yours, those explicitly
          shared with you, those shared with all site users, and those that are
          completely public
        - cursor pagination, ordered by last updated, fixed page size
- [X] api/notebooks/public
        - GET returns all public notebooks
        - cursor pagination, ordered by last updated, fixed page size
- [X] api/notebooks/internal
        - GET returns all internal notebooks
        - cursor pagination, ordered by last updated, fixed page size
- [X] api/notebooks/private
        - GET returns all private notebooks you own or are explicitly shared
          with you
        - cursor pagination, ordered by last updated, fixed page size
- [X] api/notebooks/{user}/
        - GET returns all notebooks owned by that user that you have access to
        - cursor pagination, ordered by last updated, fixed page size
- [X] change `url` to API URL, add `html_url` for website URL (fully qualified)
- [X] add `editable` boolean to notebook representation


# notebook content @phase

- [X] api/notebooks/{user}/{notebook}/
        - GET returns list of pages with metadata (but no content),
          including deletions
        - cursor pagination, ordered by last updated, fixed page size
        - ?since=_timestamp_ only pages updated after that point, including
          deletions
- [X] include `editable` boolean in notebook metadata
- [X] include content hash


# page content @phase

- [X] api/notebooks/{user}/{notebook}/{uuid}
        - GET returns raw content with Content-Type header
        - ?version=_ver_ for older versions
- [X] PUT to update the page's content, creating a new version
        - raw body with Content-Type header
        - response includes previous hash for conflict detection
- [X] PATCH to update the page's metadata (path)
- [X] PATCH to revert to older version
- [X] DELETE to soft-delete the page
- [ ] PATCH to restore deleted page
        - `{"restore": true}` restores to original location
        - `{"restore": true, "filename": "new.md"}` restores to new location
        - returns conflict if target location is occupied
- [X] POST api/notebooks/{user}/{notebook}/
        - multipart, file (required), filename (optional, overrides same as
          website)
- [X] reject uploads without file extension
        - prevents path conflicts between files and directories


# test coverage @phase

- [ ] PUT returns conflict when restoring deleted page with occupied path
- [ ] test that `url` fields in API responses can be followed all the way down
- [ ] assert error response bodies in tests, not just status codes
- [ ] ensure API docs accurately describe error response structure
- [ ] ensure API docs accurately describe responses
- [ ] ensure restore arg to PATCH is rejected if the file is not soft-deleted
