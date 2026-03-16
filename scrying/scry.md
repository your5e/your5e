# Scrying

Configuration for `scry.py`, which takes screenshots of the site at multiple viewport widths.

## Widths

Default viewport widths for all pages:

```toml
[widths]
desktop = 1280
tablet = 768
mobile = 375
```

## Users

Credentials for authenticated pages (username = password):

```toml
[users]
norm = "norm"
wendy = "wendy"
```

## Pages

Each page is defined with `[pages.name]`:

```toml
[pages.site-home]
path = "/"
```

The table name becomes the screenshot filename prefix.

### Options

| Option | Description |
| ------ | ----------- |
| `path` | URL path to visit |
| `user` | Username to authenticate as (from `[users]`) |
| `steps` | Actions to perform after navigating to path |
| `widths` | Subset of default widths to use |
| `add_widths` | Additional widths to include |

### Custom Widths

Use all defaults (omit `widths`):

```toml
[pages.home]
path = "/"
```

Use subset of defaults:

```toml
[pages.home]
path = "/"
widths = ["desktop", "mobile"]
```

Add extra width:

```toml
[pages.home]
path = "/"
add_widths = [{ name = "narrow", value = 320 }]
```

Replace defaults entirely:

```toml
[pages.home]
path = "/"
widths = []
add_widths = [{ name = "custom", value = 1000 }]
```

### Steps

For pages that require interaction before screenshotting:

```toml
[pages.form-submitted]
user = "norm"
path = "/form"
steps = [
    { fill = { field = "name", value = "Some value" } },
    { fill = { field = "description", value = "Some text" } },
    { click = { text = "Submit" } },
]
```

Step types (all accept optional `timeout` in ms, default 2000):

- `form` - scope subsequent steps to a form (for pages with multiple forms)

    ```toml
    { form = { selector = "form:first-of-type" } }
    { form = { selector = "#slow-form", timeout = 5000 } }
    ```

- `fill` - fill a form field by its name attribute

    ```toml
    { fill = { field = "email", value = "test@example.com" } }
    ```

- `click` - click an element by `text`, `selector`, or both `text` and `role`
    - `text` - visible text of the element
    - `role` - ARIA role (button, link, checkbox, etc.) to narrow matches
    - `selector` - CSS selector

    ```toml
    { click = { text = "Help" } }
    { click = { text = "Submit", role = "button" } }
    { click = { selector = ".submit-btn" } }
    ```
