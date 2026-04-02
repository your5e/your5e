import re

import bleach
import markdown


def render_wiki_content(text, resolve_wikilink, base_url):
    def replace_image_embed(match):
        content = match.group(1)
        if "|" in content:
            target, dimensions = content.split("|", 1)
        else:
            target = content
            dimensions = None

        path = resolve_wikilink(target)

        dims = ""
        if dimensions:
            if "x" in dimensions:
                width, height = dimensions.split("x", 1)
                dims = f' width="{width}" height="{height}"'
            else:
                dims = f' width="{dimensions}"'

        return f'<img src="{base_url}/{path}"{dims}>'

    def replace_wikilink(match):
        content = match.group(1)
        if "|" in content:
            target, display = content.split("|", 1)
        else:
            target = content
            display = target

        path = resolve_wikilink(target)

        return f"[{display}]({base_url}/{path})"

    base_url = base_url.rstrip("/")

    text = bleach.clean(text, tags=[], strip=True)
    text = re.sub(r"!\[\[([^\]]+)\]\]", replace_image_embed, text)
    text = re.sub(r"\[\[([^\]]+)\]\]", replace_wikilink, text)
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])

    return html
