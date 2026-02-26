import re
from posixpath import normpath

import markdown


def render_wiki_content(text, resolve_wikilink, base_url, current_dir=None):
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

        return f'<img src="/{path}"{dims}>'

    def replace_wikilink(match):
        content = match.group(1)
        if "|" in content:
            target, display = content.split("|", 1)
        else:
            target = content
            display = target

        path = resolve_wikilink(target)

        return f"[{display}](/{path})"

    def replace_url(match):
        attr = match.group(1)
        url = match.group(2)

        if url.startswith(("http://", "https://", "#")):
            return match.group(0)

        if url.startswith("/"):
            resolved = f"{base_url}{url}"
        else:
            if current_dir:
                resolved = f"{base_url}/{normpath(current_dir + '/' + url)}"
            else:
                resolved = f"{base_url}/{normpath(url)}"

        return f'{attr}="{resolved}"'

    base_url = base_url.rstrip("/")

    text = re.sub(r"!\[\[([^\]]+)\]\]", replace_image_embed, text)
    text = re.sub(r"\[\[([^\]]+)\]\]", replace_wikilink, text)
    html = markdown.markdown(text, extensions=["fenced_code"])
    html = re.sub(r'(href|src)="([^"]+)"', replace_url, html)

    return html
