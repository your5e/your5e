A collection of notebooks in a campaign is to be treated like a fully-fledged
Obsidian vault/wiki. The base of the wiki is a Notebook. It is created with
the campaign, owned by the owner of the campaign and cannot be unlinked or
deleted.

# Preparation @phase

- [X] refactor the notebook views to be ready for being a subclass used by
      campaign views
        - they should be rewritten to be proper class-based views, not a
          weird hybrid of class and functions
        - the edit page should be an UpdateView, with '?edit' switching
          the handling view

# Create the campaign wiki @phase

- [X] add a campaign notebook to the campaign when it is created
        - it is autocreated ("campaign name wiki"), private visibility
        - it cannot be deleted or unlinked from the campaign
        - it cannot be moved from order 0, other notebooks cannot rise past 1
- [X] ensure notebook ownership transfers with campaign ownership
- [X] anyone joining the campaign gets read/write permission automatically
- [X] deleting a campaign does not require confirmation if the notebook
      is empty


# Bring in notebooks @phase

Notebooks added to a campaign should be integrated into the "wiki" as a
folder -- adding a "Campaign Notes" notebook would make its resolution path
`/campaign/user/slug/wiki/campaign-notes`, slug defaults to `notebook.slug`
on link, append numbers as we do elsewhere to differentiate when colliding.

- [ ] add campaign wiki aware notebook URLs
        - adds a third layer of navigation, global, campaign, notebook,
          breadcrumbs?
        - links in notebook pages should remain in the campaign context
        - attached notebook beats paths in the wiki, warn when adding a
          notebook that would clash
- [ ] extend wikilink resolution to be campaign-aware
        - shortest-path, first-notebook-match as tiebreaker using the campaign
          attachment ordering (test both ways)
- [ ] creating a page in the campaign wiki should offer a dropdown of which
      place it gets created
        - defaults to the current context (either wiki or notebook)
        - read-only notebooks are excluded
        - ensure returns to campaign context not notebook
