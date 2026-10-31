"""Render annotated resume Markdown as HTML using the shared Mistune parser."""

import argparse
from html import escape, unescape
from pathlib import Path
import re
import unicodedata

import mistune

from resume_parser import Field, Node, Resume, parse_resume


PRELUDE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap" rel="stylesheet">
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/gh/bitmaks/cm-web-fonts@latest/fonts.css">
    <link rel="stylesheet" href="./css/normalize.css">
    <link rel="stylesheet" href="./css/style.css">
</head>
<body>
<div class="container">
"""

CONCLUSION = """</div>
</body>
</html>
"""


def _plain_text(nodes: list[Node]) -> str:
    return "".join(
        unescape(node["text"]) if node["type"] == "text" else
        node["text"] if node["type"] == "codespan" else
        " " if node["type"] == "linebreak" else
        _plain_text(node.get("children", []))
        for node in nodes
    )


class _ResumeHTMLRenderer(mistune.HTMLRenderer):
    def __init__(self, section_ids: set[str]):
        super().__init__()
        self.heading_ids = set(section_ids)

    def text(self, text):
        return escape(unescape(text))

    def link(self, link, text=None, title=None):
        attributes = f' href="{self._safe_url(link)}" target="_blank" rel="noopener noreferrer"'
        if title:
            attributes += f' title="{escape(unescape(title))}"'
        return f'<a{attributes}>{text if text is not None else self.text(unescape(link))}</a>'

    def render_heading(self, nodes: list[Node], level: int, identifier: str | None = None) -> str:
        if identifier is None:
            text = unicodedata.normalize("NFKD", _plain_text(nodes)).encode("ascii", "ignore").decode("ascii")
            slug = re.sub(r"[^a-z0-9_]+", "-", text.lower()).strip("-") or "heading"
            identifier = slug
            suffix = 1
            while identifier in self.heading_ids:
                identifier = f"{slug}-{suffix}"
                suffix += 1
            self.heading_ids.add(identifier)
        return f'<h{level} id="{escape(identifier)}">{self.render_nodes(nodes)}</h{level}>\n'

    def render_inline_field(self, value: Field | None) -> str:
        return self.render_nodes(value.nodes[0]["children"]) if value is not None else ""

    def render_nodes(self, nodes: list[Node]) -> str:
        result = []
        for node in nodes:
            kind = node["type"]
            if kind == "text":
                result.append(self.text(node["text"]))
            elif kind == "codespan":
                result.append(self.codespan(node["text"]))
            elif kind == "linebreak":
                result.append(self.linebreak())
            elif kind == "heading":
                result.append(self.render_heading(node["children"], node["level"]))
            else:
                children = self.render_nodes(node["children"])
                if kind == "link":
                    result.append(self.link(node["link"], children, node.get("title")))
                elif kind == "list":
                    result.append(self.list(children, node["ordered"], node["level"], node.get("start")))
                elif kind == "list_item":
                    result.append(self.list_item(children, node["level"]))
                elif kind in {"paragraph", "block_text", "strong", "emphasis"}:
                    result.append(getattr(self, kind)(children))
                else:
                    raise ValueError(f"unsupported Markdown node {kind!r}")
        return "".join(result)


def render_html(resume: Resume) -> str:
    """Render a validated resume, preserving inline whitespace and CSS hooks."""
    renderer = _ResumeHTMLRenderer({section.id for section in resume.sections})
    name = resume.header.fields["name"].nodes[0]["children"]
    title = escape(" ".join(_plain_text(name).split()) + " Resume")
    parts = [PRELUDE.format(title=title), "<header>\n", renderer.render_heading(name, 1)]
    contacts = resume.header.fields.get("contacts")
    if contacts is not None:
        parts.append(renderer.render_nodes(contacts.nodes))
    parts.append("</header>\n")

    for section in resume.sections:
        parts.append(f'<section class="{escape(section.id)}">\n')
        heading = section.fields["heading"].nodes[0]["children"]
        parts.append(renderer.render_heading(heading, 2, section.id))
        if section.layout == "entries":
            for entry in section.entries:
                for prefix, css_class in [("title", "title"), ("subtitle", "sub-title")]:
                    if prefix == "subtitle" and "subtitle-left" not in entry.fields:
                        continue
                    left = renderer.render_inline_field(entry.fields[f"{prefix}-left"])
                    right = renderer.render_inline_field(entry.fields.get(f"{prefix}-right"))
                    parts.append(f'<figure class="{css_class}"><p>{left}</p><p>{right}</p></figure>\n')
                body = entry.fields.get("body")
                if body is not None:
                    parts.append(renderer.render_nodes(body.nodes))
        else:
            parts.append(renderer.render_nodes(section.fields["body"].nodes))
        parts.append("</section>\n")
    parts.append(CONCLUSION)
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    directory = Path(__file__).resolve().parent
    source = directory / "resume.md"
    print("Reading markdown")
    resume = parse_resume(source.read_text(encoding="utf-8"), source=str(source))
    html = render_html(resume)
    print("Writing html")
    (directory / "html" / "resume.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()

