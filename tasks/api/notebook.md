@after api.md ../notebooks/model.md

REST endpoints for Notebooks.

# notebook @phase

- [ ] notebook/all
        - GET returns list of pages with metadata (but no content),
          including deletions
- [ ] notebook/path **PATH**
        - GET returns list of pages _under that point_
- [ ] notebook/changes **TIMESTAMP**
        - GET returns list of pages that have an updated date after that point,
          including deletions

# page @phase

- [ ] notebook/page _id/path_, _version_
        - addressing by ID survives the file being renamed, path does not
        - OPTIONS shows your permission to view or update
        - GET returns metadata and content, optionally specifing
          an earlier version
        - POST updates the page content and/or metadata, _cannot create_
        - PUT creates a new page, _cannot update_
        - DELETE deletes the page
