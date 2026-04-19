# Folder Sync Obsidian Plugin

This plugin for Obsidian will synchronise your notebooks as folders within
your vault.

It sends your changes to the site, then pulls any other changes back,
running approximately every five minutes.

In the event both you and someone else have modified a page, your local copy
will take precedence, overwriting it. However, the site does keep copies of
previous edits so nothing should be lost.


## Installation

This is a manual process as the plugin is still experimental, and not
yet submitted to the plugin repository.

1.  Download the [plugin zip (v0.0.3)](/static/downloads/your5e-folder-sync-0.0.3.zip)
    and unpack it.
2.  Copy the two files into your vault, under `.obsidian/plugins/your5e-folder-sync`.
3.  In Obsidian Settings, under "Community plugins", turn on community plugins
    if you haven't already. Then under "Installed plugins", turn on
    "Your5e Folder Sync".


## Configuration

Before you can sync, you will need a token that identifies you to the API,
which you can create in [your profile](/profile/). Add a new token,
calling it something memorable like "obsidian plugin". The token will be
displayed only once. Copy the token and add it to the plugin settings.

The API Base URL setting allows you to override where the plugin syncs to
if necessary, generally you can ignore this.

Next, add the folder to synchronise:

- **Folder** — the folder within your vault, such as `Monsters`. It can be
  a folder within another folder, such as `Monsters/SRD 5.2`.

    Changing this setting later will rename the folder in your vault. Renaming
    the folder in your vault will likewise update this setting automatically.

- **Notebook ID** — the ID of the notebook on the site. This can be found
  under the notebook's settings page, or you can copy/paste it from the
  URL when in your notebook. It will look like `norm/campaign-notes`.

- **Pull-only** — if you wish to only take a copy of a notebook, turn this
  option on. You can still make local changes which will persist, and the
  plugin will never push those changes. If you do not have editing
  permissions for a notebook pull-only mode is done automatically, regardless
  of this setting.

Again, if needed, you can override the API URL and token here, and generally
you would ignore these two settings as well.
