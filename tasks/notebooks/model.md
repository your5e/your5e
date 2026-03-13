@after ../users/profile.md ../wikis/model.md

A Notebook is a set of notes used in a Campaign. It is the user-facing wrapper
around a Wiki, providing ownership, and collaboration permissions.

Notebook model (inherits from Wiki):
- name
- slug (derived from name)
- owner
- visibility (private/internal/public) -- restricts viewing of pages
- copied_from (another Notebook)

NotebookPermission model:
- notebook
- user
- role (editor, viewer)


- [X] manage notebooks from user profile
        - names are not unique
        - slug is unique per owner, 'notes-2' enforced for clashing names
        - names can be updated, generating a new slug
- [X] rename middle visibility to 'internal'
