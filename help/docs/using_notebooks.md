# Using Notebooks

Notebooks are folders of notes for collecting and sharing your campaign
materials. A notebook can be shared among players, and among campaigns,
such as:

- the DM keeps a private notebook of locations, NPCs, and adventure hooks
  for one particular campaign she is running
- the DM keeps a private but common notebook of monster statblocks, added to
  all the games she runs
- the DM keeps a public notebook of ideas for one-shots and campaigns, to
  sell future ideas to her friends
- one player keeps a private notebook of thoughts and observations that his
  character has during the campaign
- another player likes to play party record keeper, and they keep a notebook
  of session notes, lore, rumours, and the history of the world they have
  learned, which they share to everyone in the campaign


## Creating a Notebook

You can [create as many notebooks](/notebooks/create) as
you need, whether to keep to yourself or share with others — also from
[your profile](/profile/), a [campaign page](/campaigns/), or
[your list of notebooks](/notebooks/mine), almost anywhere notebooks are
used you can be prompted to add a new one.


## Pages

Notebook pages are written in [Markdown](https://www.markdownguide.org),
a plain-text method of creating structured and styled content. Check the
guide for more detailed descriptions, but some common features of
Markdown are:

- Headings of different levels are created with `# Hashes`
- Bulleted lists are created with `- hyphens at the start of the line`,
  or `* asterisks`, or `+ pluses`
- Numbered lists are created with `1. a number and a period at the start of
  the line`, or `2) a number and close parenthesis`
- **Bold** text is created by surrounding words with `**double asterisks**`
- _Underlined_ text is created by surrounding words with `_underscores_`
  or `*single asterisks*`


## Page names

Pages have names, and these can include the folder you want to put the page
in, for example `Campaign Notes/Session One`. Folders are automatically
created.

The only special name is `index`, which is presented as the introductory
content of the notebook as a whole, or of a folder within the notebook, when
using a name like `Campaign Notes/index`. It can be useful to create a more
meaningful table of contents than just a list of page names, for example.


## Linking pages together

A link to a different page is created with `[[double square brackets]]`.
This will link to a page with that name wherever in the Notebook it might
appear.

If multiple pages in different folders have the same name, pages in shallower
folders will be preferred, or the first alphabetical match.


### Campaign wikis

If the notebook is a part of a campaign wiki, the link could take you to a
page in another notebook.

If multiple pages with the same name exist in multiple notebooks in a campaign
wiki, the one highest in the campaign's list will be chosen.


## Versions and deleted pages

Any saved change to a page causes a new version, but the site keeps previous
versions around. Any deleted page is similarly kept and can be restored with
all versions, for at least thirty days before being purged.


## Sharing the notebook

By default, notebooks are created private to you. You have two ways of sharing
it with others from the notebook's settings page:

- **Visibility** — You can make the notebook visible to users of the site,
  or even make it completely public.
- **Collaborators** — Rather than a blanket all-users setting, you can choose
  a small list of individuals who can see your notebook. You can also allow
  some users the right to modify your notebook.

Linking a notebook to a campaign does not automatically give any permissions,
you still have to choose to share it with the other players. This allows you
to keep your notes private but still easily found from the campaign page.


## Describing the notebook

You can add a short description to your notebook, that will appear in some
notebook lists, as a way to help others understand the purpose of the
notebook. In the main `index` page, add to the very top of the page:

```markdown
---
notebook: Notes and lore for our Lost Kingdom campaign
---

... rest of page ...
```
