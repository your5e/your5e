@after ../users/model.md

The wiki is the underlying system for storing versioned documents. It has
no opinions about URLs, ownership, or permissions, it is a foundation from
which other models such as Notebooks will build versioned content.

Implementations of Wikis, such as campaign notebooks, game rules, help and
system information, etc. inherit from using multi-table inheritance -- that
is, both Wiki and the implementation of a notebook have their own linked
tables. `notebook.page_set` should work.

`Wiki` only provides helper methods as the bridge to pages.

`Page` represents a "file" in a wiki. It provides versions.
- wiki
- deleted_at (soft deletes)

`Version` represents a page at a point in time.
- filename (can include any char but filesystem unsafe, eg "Location/Café.png")
- path (slugified filename for URL access, eg "location/cafe.png")
- mime_type
- number (stable, incremented)
- created_by
- created_at

`Content` is the content of a page version, globally hashed so that multiple
duplicate pages in multiple wikis don't take up extra storage.
- hash (primary key)
- data

- [ ] implement wiki models
        - ensure content is globally unique across all wikis
        - ensure content is shared between wikis
        - ensure pages and versions are unique to the wiki
        - ensure version numbers are unique to the page
        - ensure filename cannot end in `/`
        - ensure filename cannot contain `../`
        - page allows all characters in filename, other than `[]#^|\:*"<>?`
        - enforce path slugs are unique within the wiki,
          near duplicate filenames cannot be created
        - updating a page with identical content does not create a new version
- [ ] versions are kept when user is deleted, reassigned to sentinel

Convenience methods.

- [ ] wiki "all pages"
- [ ] wiki "changes since T"
- [ ] page update
        - update with no changes does not produce a new version
- [ ] page rename, duplicates content, new filename and path
- [ ] page history
- [ ] page revert, puts content back but with new version not deleting

Pretending there are directories by breaking on the slashes in filenames.

- [ ] wiki "list all files below dir/"
- [ ] wiki "list all folders below dir/"

Pages are not immediately purged from the database, so they can be recovered.

- [ ] deleting content directly is denied
- [ ] deleting a version within a page is possible
        - ensure page history does not break
        - ensure version numbers still increment correctly
        - ensure deleting a version only deletes content no longer referenced
- [ ] method to mark a page as deleted without removing from db
- [ ] force deleting a page is possible
        - ensure deleting a page deletes versions
- [ ] wiki does not list "deleted" pages
- [ ] wiki lists "deleted" pages separately
- [ ] wiki "purge deleted" deletes anything older than cutoff
- [ ] management command for "purge deleted"
