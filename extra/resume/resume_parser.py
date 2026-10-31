"""Parse explicit resume comment directives using Mistune 2's Markdown AST.

Containers use resume:header/endheader, section/endsection, and entry/endentry.
Each resume:field NAME owns Markdown until the next directive. Section attributes
are id and layout (entries, skills, prose); entry attributes are style
(subheading, project) and body-style (normal, footnote). Fields retain Mistune's
AST, including encoded entities, for format-specific rendering later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
import re
import shlex
from typing import Any

import mistune


Node = dict[str, Any]


class ResumeParseError(ValueError):
    """Invalid resume markup, with source and structural context."""


@dataclass
class Field:
    name: str
    line: int
    nodes: list[Node] = field(default_factory=list)


@dataclass
class Header:
    line: int
    fields: dict[str, Field] = field(default_factory=dict)


@dataclass
class Entry:
    line: int
    style: str = "subheading"
    body_style: str = "normal"
    fields: dict[str, Field] = field(default_factory=dict)


@dataclass
class Section:
    id: str
    line: int
    layout: str = "entries"
    fields: dict[str, Field] = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)


@dataclass
class Resume:
    header: Header
    sections: list[Section]


class _ResumeBlockParser(mistune.BlockParser):
    def parse_block_html(self, match, state):
        text = match.group(0).rstrip()
        line = match.string.count("\n", 0, match.start()) + 1
        comment = re.fullmatch(r" {0,3}<!--((?:(?!-->)[\s\S])*)-->[ \t]*", text)
        if comment:
            contents = comment.group(1).strip()
            if contents.startswith("resume:"):
                return {"type": "resume_marker", "raw": contents[7:], "params": (line,)}
            return {"type": "newline", "blank": True}
        return {"type": "block_html", "raw": text, "params": (line,)}


class _ResumeAstRenderer(mistune.AstRenderer):
    def resume_marker(self, text, line):
        return {"type": "resume_marker", "text": text, "line": line}

    def block_html(self, text, line):
        return {"type": "block_html", "text": text, "line": line}


def _has_content(nodes: list[Node]) -> bool:
    for node in nodes:
        text = node.get("text", "")
        if node["type"] == "text":
            text = unescape(text)
        if text.strip() or _has_content(node.get("children", [])):
            return True
    return False


class _ResumeBuilder:
    def __init__(self, source: str):
        self.source = source
        self.header: Header | None = None
        self.in_header = False
        self.section: Section | None = None
        self.entry: Entry | None = None
        self.current_field: Field | None = None
        self.sections: list[Section] = []

    def fail(self, message: str, line: int) -> None:
        context = []
        if self.in_header:
            context.append("header")
        if self.section is not None:
            context.append(f"section {self.section.id!r}")
        if self.entry is not None:
            context.append(f"entry at line {self.entry.line}")
        if self.current_field is not None:
            context.append(f"field {self.current_field.name!r}")
        suffix = f" ({', '.join(context)})" if context else ""
        raise ResumeParseError(f"{self.source}:{line}: {message}{suffix}")

    def owner(self) -> Header | Section | Entry | None:
        if self.entry is not None:
            return self.entry
        if self.section is not None:
            return self.section
        if self.in_header:
            return self.header
        return None

    def attributes(self, arguments: list[str], allowed: set[str], line: int) -> dict[str, str]:
        result = {}
        for argument in arguments:
            name, separator, value = argument.partition("=")
            if not separator or name not in allowed or not value:
                self.fail(f"invalid attribute {argument!r}; allowed: {', '.join(sorted(allowed)) or 'none'}", line)
            if name in result:
                self.fail(f"duplicate attribute {name!r}", line)
            result[name] = value
        return result

    def require(self, owner: Header | Section | Entry, names: set[str]) -> None:
        for name in sorted(names):
            if name not in owner.fields:
                self.fail(f"missing required field {name!r}", owner.line)

    def validate_nodes(self, nodes: list[Node], line: int, inside_list: bool = False) -> list[Node]:
        result = []
        for node in nodes:
            kind = node["type"]
            if kind == "newline":
                continue
            if kind == "inline_html" and re.fullmatch(r"<!--(?:(?!-->)[\s\S])*-->", node["text"]):
                if node["text"][4:-3].strip().startswith("resume:"):
                    self.fail("directives must be standalone top-level comments", line)
                continue
            if kind not in {"text", "codespan", "linebreak", "strong", "emphasis", "link",
                            "paragraph", "heading", "list", "list_item", "block_text"}:
                self.fail(f"unsupported Markdown node {kind!r}", node.get("line", line))
            if kind == "list" and inside_list:
                self.fail("nested lists are not supported", line)
            if "children" in node:
                node = dict(node, children=self.validate_nodes(node["children"], line, inside_list or kind == "list"))
            result.append(node)
        return result

    def finish_field(self) -> None:
        """Finalize the current field by validating its content and structure."""
        current = self.current_field
        if current is None:
            return
        current.nodes = self.validate_nodes(current.nodes, current.line)
        if not _has_content(current.nodes):
            self.fail("field must not be empty; omit optional fields instead", current.line)
        if current.name in {"name", "heading", "title-left", "title-right", "subtitle-left", "subtitle-right"}:
            allowed = {"paragraph", "heading"} if current.name in {"name", "heading"} else {"paragraph"}
            if len(current.nodes) != 1 or current.nodes[0]["type"] not in allowed:
                self.fail("expected a single heading or paragraph" if "heading" in allowed else "expected a single paragraph", current.line)
        elif current.name == "contacts":
            for node in current.nodes:
                if node["type"] != "paragraph" or any(
                    child["type"] != "link" and not (child["type"] == "text" and not child["text"].strip())
                    for child in node["children"]
                ):
                    self.fail("contacts must contain only links and whitespace", current.line)
        elif current.name == "body":
            owner = self.owner()
            if isinstance(owner, Section) and owner.layout == "skills" and any(
                node["type"] != "paragraph" for node in current.nodes
            ):
                self.fail("skills body must contain paragraphs", current.line)
        self.current_field = None

    def directive(self, text: str, line: int) -> None:
        if "\n" in text:
            self.fail("directives must fit on one line", line)
        try:
            parts = shlex.split(text)
        except ValueError as error:
            self.fail(f"invalid directive: {error}", line)
        if not parts:
            self.fail("empty directive", line)
        command, *arguments = parts
        self.finish_field()
        if command == "field":
            owner = self.owner()
            if owner is None:
                self.fail("field outside a container", line)
            if len(arguments) != 1:
                self.fail("field requires exactly one name", line)
            name = arguments[0]
            if isinstance(owner, Header):
                allowed = {"name", "contacts"}
            elif isinstance(owner, Entry):
                allowed = {"title-left", "title-right", "body"}
                if owner.style == "subheading":
                    allowed |= {"subtitle-left", "subtitle-right"}
            else:
                allowed = {"heading"} if owner.layout == "entries" else {"heading", "body"}
            if name not in allowed:
                self.fail(f"unknown field {name!r}; allowed: {', '.join(sorted(allowed))}", line)
            if name in owner.fields:
                self.fail(f"duplicate field {name!r}", line)
            self.current_field = Field(name, line)
            owner.fields[name] = self.current_field
        elif command == "header":
            self.attributes(arguments, set(), line)
            if self.owner() is not None or self.header is not None:
                self.fail("header must occur exactly once at top level", line)
            self.header = Header(line)
            self.in_header = True
        elif command == "section":
            attributes = self.attributes(arguments, {"id", "layout"}, line)
            if self.owner() is not None:
                self.fail("section must be top level", line)
            identifier = attributes.get("id", "")
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", identifier):
                self.fail("section requires a lowercase, hyphen-separated id", line)
            if any(section.id == identifier for section in self.sections):
                self.fail(f"duplicate section id {identifier!r}", line)
            layout = attributes.get("layout", "entries")
            if layout not in {"entries", "skills", "prose"}:
                self.fail(f"unknown section layout {layout!r}", line)
            self.section = Section(identifier, line, layout)
            self.sections.append(self.section)
        elif command == "entry":
            attributes = self.attributes(arguments, {"style", "body-style"}, line)
            if self.section is None or self.section.layout != "entries" or self.entry is not None:
                self.fail("entry requires an entries section and cannot be nested", line)
            style = attributes.get("style", "subheading")
            body_style = attributes.get("body-style", "normal")
            if style not in {"subheading", "project"}:
                self.fail(f"unknown entry style {style!r}", line)
            if body_style not in {"normal", "footnote"}:
                self.fail(f"unknown body style {body_style!r}", line)
            self.entry = Entry(line, style, body_style)
            self.section.entries.append(self.entry)
        elif command in {"endheader", "endsection", "endentry"}:
            self.attributes(arguments, set(), line)
            if command == "endheader":
                if not self.in_header:
                    self.fail("endheader without an open header", line)
                self.require(self.header, {"name"})
                self.in_header = False
            elif command == "endentry":
                if self.entry is None:
                    self.fail("endentry without an open entry", line)
                self.require(self.entry, {"title-left"})
                if "subtitle-right" in self.entry.fields:
                    self.require(self.entry, {"subtitle-left"})
                self.entry = None
            else:
                if self.section is None or self.entry is not None:
                    self.fail("endsection requires a section with no open entry", line)
                required = {"heading"} if self.section.layout == "entries" else {"heading", "body"}
                self.require(self.section, required)
                self.section = None
        else:
            self.fail(f"unknown directive {command!r}", line)

    def build(self, nodes: list[Node]) -> Resume:
        for node in nodes:
            if node["type"] == "resume_marker":
                self.directive(node["text"], node["line"])
            elif node["type"] != "newline":
                if self.current_field is None:
                    owner = self.owner()
                    self.fail("content must belong to an explicit field", node.get("line", owner.line if owner else 1))
                self.current_field.nodes.append(node)
        self.finish_field()
        owner = self.owner()
        if owner is not None:
            self.fail("unclosed container", owner.line)
        if self.header is None:
            self.fail("missing header", 1)
        return Resume(self.header, self.sections)


def parse_resume(text: str, source: str = "<resume>") -> Resume:
    """Parse annotated Markdown, raising ResumeParseError before any rendering."""
    renderer = _ResumeAstRenderer()
    markdown = mistune.Markdown(renderer=renderer, block=_ResumeBlockParser())
    return _ResumeBuilder(source).build(markdown(text))