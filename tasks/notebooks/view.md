@after model.md

Notebooks provide URL routing to their underlying wiki pages.
Views enforce permissions.

# Notebook view @phase

- [ ] owner can rename the notebook
- [ ] owner can change visibility, requires confirmation step
- [ ] owner can control collaborators on a notebook
        - owner can alter visibility
        - owner can add and remove collaborators, requires confirmation step
        - owner can change collaborator role, requires confirmation step
        - permissions only listed to other collaborators
- [ ] ensure non-owner cannot change notebook or collaborators

# Notebook index pages @phase

Shared with the main notebook view, presents other "folders" and pages
logically "under" this folder. If `.../index.md` exists, it is folded in.

- [ ] list of "folders"
        - only authorised viewers
- [ ] list of pages "at" this folder
        - edit links for owners and editors
        - restore buttons for deleted pages for owners and editors
- [ ] upload a new page
        - only owners and editors
        -limit content uplaods to 2mb, ensuring new version not made if too big
- [ ] link to edit `index.md`
        - only owners and editors


# Notebook viewing @phase

View a page, either Markdown converted to HTML, or the raw uploaded file.

- [ ] view page
        - accepts Markdown paths without `.md`
        - redirects Markdown paths with `.md` to without
- [ ] lists and views older versions
        - ignore path differences on older versions
- [ ] unresolved path gives creation form/edit page
- [ ] ensure links in Markdown are resolving correctly
        - relative to current "directory"
        - absolute paths relative to notebook


# Notebook edit @phase

Edit a page -- upload new content, change the filename, delete.

- [ ] edit page
        - only owners and editors can see and use
        - offers upload to replace content
- [ ] saving to non-existence page creates
        - ensure `.md` added to filename if left out
        - current "directory" added by default to filename
        - no filename is error
- [ ] changing filename renames before updating content
        - redirects to new path
- [ ] delete shows confirmation


# Notebook permissions check @phase

Ensure the default is deny, override as stated:

- [ ] ensure permissions are enforced
        - editors can see and modify pages in private notebooks (it overrides)
        - viewers can see pages in private notebooks (it overrides)
        - other site users cannot see pages private notebooks
        - editors can see and modify pages in site notebooks
        - viewers can see pages in site notebooks
        - other site users can see pages site notebooks
        - site users can see pages in public notebooks
        - anonymous can see pages in public notebooks
