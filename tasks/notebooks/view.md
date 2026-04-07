@after model.md

Notebooks provide URL routing to their underlying wiki pages.
Views enforce permissions.

# Notebook view @phase

- [X] owner can rename the notebook
- [X] owner can change visibility, requires confirmation step
- [X] owner can control collaborators on a notebook
        - owner can add and remove collaborators, requires confirmation step
        - owner can change collaborator role, requires confirmation step
        - permissions only listed to other collaborators
- [X] ensure non-owner cannot change notebook or collaborators
- [X] owner can delete notebook, requires confirmation step
        - empty it first?
        - what about collaborators?


# Notebook index pages @phase

Shared with the main notebook view, presents other "folders" and pages
logically "under" this folder. If `.../index.md` exists, it is folded in.

- [X] list of "folders"
        - only authorised viewers
- [X] list of pages "at" this folder
        - edit links for owners and editors
        - restore buttons for deleted pages for owners and editors
- [X] upload a new page
        - only owners and editors
        - limit content uploads to 2mb, ensuring new version not made if too big
        - use mimetypes.guess_type to set the mime type, fallback to common
          extensions if this fails, otherwise a useful default
- [X] link to edit `index.md`
        - only owners and editors
- [X] clarify what uploading a file with an existing filename does
        - add tests to document the current behaviour
        - decide if it should update the existing page or error


# Notebook viewing @phase

View a page, either Markdown converted to HTML, or the raw uploaded file.

- [X] view page
        - accepts Markdown paths without `.md`
        - redirects Markdown paths with `.md` to without
- [X] lists and views older versions
        - ignore path differences on older versions
- [X] ensure links in Markdown are resolving correctly
        - relative to current "directory"
        - absolute paths relative to notebook
- [X] sanitise HTML in wiki content before markdown rendering


# Notebook edit @phase

Edit a page -- upload new content, change the filename, delete.

- [X] edit page
        - only owners and editors can see and use
        - offers upload to replace content
- [X] unresolved path gives creation form/edit page
- [X] saving to non-existence page creates
        - ensure `.md` added to filename if left out
        - current "directory" added by default to filename
        - no filename is error
- [X] changing filename renames before updating content
        - redirects to new path
- [X] delete shows confirmation
- [X] upload file resets mime type and filename
- [X] restore deleted page
        - redirects to notebook index
- [X] restore with optional filename
        - allows us to bypass conflicts
        - ensures there is no new conflict
- [X] ensure trailing newlines always


# Notebook permissions check @phase

Ensure the default is deny, override as stated:

- [X] ensure permissions are enforced
        - editors can see and modify pages in private notebooks (it overrides)
        - viewers can see pages in private notebooks (it overrides)
        - other site users cannot see pages private notebooks
        - editors can see and modify pages in site notebooks
        - viewers can see pages in site notebooks
        - other site users can see pages site notebooks
        - site users can see pages in public notebooks
        - anonymous can see pages in public notebooks


# Notebook creation @phase

Refactor notebook creation into its own view at `/notebooks/create` so it can
be used from both the profile page and campaign page.

- [X] create `/notebooks/create` view
        - set visibility
        - set collaborators (list)
        - redirect to notebook
- [X] profile page and campaign page uses
- [X] notebook contains links to owner and to campaigns it appears in
- [X] description textarea, creates index.md by default


# Notebook management views @phase

The notebook index page was a placeholder to test functionality, but for real
use it has too many responsibilities.

Notebooks support user-specified paths, so management views cannot use URLs
under the notebook's base path (e.g. `/notebooks/<user>/<slug>/settings/`)
as this would block users from creating pages at that path.

- [X] create and use NotebookSettingsView
        - collaborator management
        - visibility controls
        - rename notebook
        - delete notebook
        - remove existing from index page
- [X] adding an empty collaborator is not an error, redirect back to settings
- [X] adding an unknown collaborator is a correctable error,
      redraw form with error not 404
- [X] not deleting a notebook redirects back to settings
- [X] not changing visibility redirects back to settings
- [X] renaming notebook requires confirmation, cancel redirects back to settings
- [X] create and use NotebookDeletedPagesView
        - lists deleted page details and provide restore buttons
        - remove existing from index page
- [X] create and use NotebookPageCreateView
        - create new markdown page
        - upload new file
        - remove existing from index page
- [X] refactor notebook tests into smaller, focused test files


# Notebook navigation @phase

Per-notebook nagivation stripe for control options. Second stripe for
breadcrumbs.

- [X] Add nagivation stripe
- [X] Add breadcrumbs


# Notebook parent pages @phase

We should not have dead pages in the URL hierarchy.

- [X] `/notebooks/{user}/` redirects to list
- [X] `/notebooks/` lists the notebooks the user owns and can edit
