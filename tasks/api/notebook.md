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
- [ ] change `url` to API URL, add `html_url` for website URL (fully qualified)


# notebook content @phase

- [X] api/notebooks/{user}/{notebook}/
        - GET returns list of pages with metadata (but no content),
          including deletions
        - cursor pagination, ordered by last updated, fixed page size
        - ?since=_timestamp_ only pages updated after that point, including
          deletions


# page content @phase

- [ ] api/notebooks/{user}/{notebook}/{path}
      api/notebooks/{user}/{notebook}/{uuid}
        - addressing by ID survives the file being renamed, path does not
        - OPTIONS shows your permission to view or update
        - GET returns metadata and content, ?version=_ver_ for older
        - POST updates the page content and/or metadata, _cannot create_
        - PUT creates a new page, _cannot update_
        - DELETE deletes the page
