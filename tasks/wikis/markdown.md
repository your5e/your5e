@after model.md
@queue

Support the conversion of Markdown in wiki pages, anything with the mime type
"text/markdown".

- [X] render standard Markdown elements
- [ ] do not render frontmatter
- [ ] redact/escape embedded HTML
- [X] relative and absolute paths in hrefs resolve to a given base
- [X] match wikilinks to pages
        - ignores `.md`
        - resolution: exact case insensitive, normalised (spaces, hyphens, underscores),
          shortest path wins when multiple "files" matched
        - no matching page links as though found at path
- [X] render image embeds, including with dimensions (`|300` and `|640x480`)
- [ ] render Obsidian callouts
- [ ] render transclusion of full page, section, block
- [ ] render tables
- [ ] render mermaid diagrams
- [ ] render other Obsidian Flavoured Markdown
