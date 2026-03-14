@after ../users/profile.md

Users can create campaigns. A campaign is the top-level container for a game.
The campaign owner invites players by giving them the join URL, which contains
a randomly generated code.

Campaign model:
- owner
- name (unique to owner, not globally)
- slug (made from name)
- description (Markdown)
- join_slug (created randomly)
- players

- [X] manage campaigns from user profile
        - lists all campaigns user is in or owns
        - user can create a new campaign
        - user can delete a campaign they own
        - user can leave a campaign

- [X] campaign page for modifying campaign
        - owner can rename (updates the slug, checking for collision)
        - owner can update the description
        - owner can recreate join URL, old one immediately stops working
        - owner can remove players
        - page shows join URL
        - page lists owner and players
        - players can leave campaigns

- [X] players join campaigns via join page
        - must confirm, not automatic, redirects to campaign
        - can only join once, "go to campaign"
        - anonymous user sent to login with `next` param

- [X] campaigns reassigned to sentinel on user deletion
        - if there are still players (if not, delete)
        - any player can claim the campaign and become the new owner
        - owners can leave campaigns triggering this

- [X] `/campaigns/create` is the form, not on the profile
- [ ] deleting a campaign does not require confirmation when it has nothing attached
- [ ] `/campaigns/` ... shows what?
