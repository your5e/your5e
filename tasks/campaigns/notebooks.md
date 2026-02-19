@after model.md ../notebooks/model.md

Notebooks can be linked to multiple campaigns, allowing shared content
(house rules, setting lore) across campaigns.

CampaignNotebook:
- linked_by
- order

- [ ] campaign page allows linking a notebook
        - anyone in the campaign can link a notebook they own
        - anyone in the campaign can link a public notebook
        - same notebook cannot be linked twice
        - same notebook can be linked in multiple campaigns
- [ ] campaign page allows removing a notebook
        - the owner of the campaign can remove any notebook
        - the owner of a notebook can remove that notebook
        - the user who linked a notebook can remove that notebook
- [ ] notebooks list their owner and collaboration permissions
- [ ] notebooks appear in order
        - notebooks are added to the bottom
        - campaign owner can re-order
- [ ] a linked notebook does not override the notebook's inherent permissions
        - a user can link their private notes, other users of the campaign
          still cannot see them
        - should it be listed anyway?
        - notebook owner is shown a warning if the notebook is not visible
          to a user in the campaign

- [ ] suggest public notebooks @after ../notebooks/public/public.md
