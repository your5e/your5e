import mimetypes

MIME_TYPE_FALLBACKS = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
DEFAULT_MIME_TYPE = "application/octet-stream"


def guess_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()
        else:
            ext = ""
        mime_type = MIME_TYPE_FALLBACKS.get(ext, DEFAULT_MIME_TYPE)
    return mime_type
