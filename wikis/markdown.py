import re

import bleach
import markdown

ALLOWED_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "pre", "code", "hr", "br",
    "ul", "ol", "li",
    "a", "em", "strong", "img",
    "table", "thead", "tbody", "tr", "th", "td",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "width", "height", "alt", "title"],
}


CODE_AND_WIKILINK_PATTERN = re.compile(
    r"(```[\s\S]*?```)"    # fenced code block
    r"|(`[^`]+`)"          # inline code
    r"|!\[\[([^\]]+)\]\]"  # image embed (content in group 3)
    r"|\[\[([^\]]+)\]\]"   # wikilink (content in group 4)
)


def render_wiki_content(text, resolve_wikilink, base_url):
    def make_image_embed(content):
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

    def make_wikilink(content):
        if "|" in content:
            target, display = content.split("|", 1)
        else:
            target = content
            display = target

        path = resolve_wikilink(target)

        return f"[{display}]({base_url}/{path})"

    def replace_wikilinks(match):
        if match.group(1) or match.group(2):
            return match.group(0)
        if match.group(3):
            return make_image_embed(match.group(3))
        if match.group(4):
            return make_wikilink(match.group(4))
        return match.group(0)

    base_url = base_url.rstrip("/")

    text = CODE_AND_WIKILINK_PATTERN.sub(replace_wikilinks, text)
    html = markdown.markdown(text, extensions=["fenced_code", "tables"])
    html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)

    return html
