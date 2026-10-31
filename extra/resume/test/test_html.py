from html.parser import HTMLParser
from pathlib import Path
import unittest
from xml.etree.ElementTree import Element, SubElement

from gen_html import render_html
from resume_parser import parse_resume
from resume_fixtures import HEADER, section


class _HTMLDocument(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(html)
        self.close()
        if len(self.stack) != 1:
            raise ValueError("unclosed HTML elements")

    def handle_starttag(self, tag, attrs):
        element = SubElement(self.stack[-1], tag, dict(attrs))
        if tag not in {"meta", "link", "br"}:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in {"meta", "link", "br"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise ValueError(f"unbalanced HTML element {tag!r}")
        self.stack.pop()

    def handle_data(self, data):
        parent = self.stack[-1]
        if len(parent):
            parent[-1].tail = (parent[-1].tail or "") + data
        else:
            parent.text = (parent.text or "") + data


class ResumeHTMLTests(unittest.TestCase):
    def document(self, source):
        return _HTMLDocument(render_html(parse_resume(source))).root

    def test_repository_html_structure_and_content(self):
        source = Path(__file__).resolve().parents[1] / "resume.md"
        document = self.document(source.read_text(encoding="utf-8"))
        name = document.find(".//header/h1")
        self.assertEqual("".join(name.itertext()), "Mat\u00e9i Cloteaux")
        self.assertEqual(name.get("id"), "matei-cloteaux")
        self.assertEqual(document.find(".//title").text, "Mat\u00e9i Cloteaux Resume")
        sections = document.findall(".//section")
        self.assertEqual([item.get("class") for item in sections], ["education", "experience", "projects", "technical-skills"])
        self.assertEqual([item.find("h2").get("id") for item in sections], ["education", "experience", "projects", "technical-skills"])
        figures = document.findall(".//figure")
        self.assertEqual(len(figures), 12)
        self.assertTrue(all([child.tag for child in figure] == ["p", "p"] for figure in figures))
        self.assertEqual(sum(figure.get("class") == "title" for figure in figures), 7)
        self.assertEqual(sum(figure.get("class") == "sub-title" for figure in figures), 5)
        self.assertEqual(len(document.findall(".//li")), 16)
        self.assertEqual(len(document.findall(".//header/p/a")), 3)
        self.assertEqual(len(document.findall(".//a")), 5)
        for anchor in document.findall(".//a"):
            self.assertEqual(anchor.get("target"), "_blank")
            self.assertEqual(anchor.get("rel"), "noopener noreferrer")
        visible = " ".join("".join(document.itertext()).split())
        self.assertIn("using AWS services", visible)
        self.assertNotIn("Courses:", visible)
        self.assertNotIn("resume:", visible)
        stylesheets = [item.get("href") for item in document.findall(".//link") if item.get("rel") == "stylesheet"]
        self.assertIn("./css/style.css", stylesheets)
        self.assertNotIn("./css/style-local.css", stylesheets)

    def test_custom_source_order_and_stable_section_heading_ids(self):
        source = section("research", "Renamed heading") + HEADER + section("work", "Another heading")
        document = self.document(source)
        container = document.find(".//div")
        self.assertEqual([item.tag for item in container], ["header", "section", "section"])
        self.assertEqual([item.get("id") for item in document.findall(".//section/h2")], ["research", "work"])

    def test_missing_optional_fields_keep_two_stable_columns(self):
        entry = "<!-- resume:entry -->\n<!-- resume:field title-left -->\nOnly title\n<!-- resume:endentry -->\n"
        document = self.document(HEADER + section(entry=entry))
        figures = document.findall(".//figure")
        self.assertEqual(len(figures), 1)
        self.assertEqual(len(figures[0].findall("p")), 2)
        self.assertIsNone(figures[0][1].text)
        minimal_header = "<!-- resume:header -->\n<!-- resume:field name -->\nName\n<!-- resume:endheader -->\n"
        self.assertIsNone(self.document(minimal_header).find(".//header/p"))

    def test_inline_formatting_and_entities_do_not_add_whitespace_or_markup(self):
        entry = """<!-- resume:entry style=project -->
<!-- resume:field title-left -->
**[Project](https://example.com?a=1&b=2#part "A &amp; B")** | *Python*
<!-- resume:field body -->
**bold**ness &#42;literal&#42; &lt;script&gt; &amp; `&lt;code&gt;`
<!-- resume:endentry -->
"""
        document = self.document(HEADER + section(entry=entry))
        body = document.find(".//section/p")
        self.assertEqual("".join(body.itertext()), "boldness *literal* <script> & &lt;code&gt;")
        self.assertIsNone(document.find(".//script"))
        anchor = document.find(".//figure/p/strong/a")
        self.assertEqual(anchor.get("href"), "https://example.com?a=1&b=2#part")
        self.assertEqual(anchor.get("title"), "A & B")
        self.assertEqual("".join(document.find(".//figure/p").itertext()), "Project | Python")

    def test_mistune_url_safety_is_preserved(self):
        source = HEADER.replace("mailto:matei@example.com", "javascript:alert%281%29")
        anchor = self.document(source).find(".//header/p/a")
        self.assertEqual(anchor.get("href"), "#harmful-link")

    def test_custom_layouts_body_headings_and_ordered_lists(self):
        source = """<!-- resume:section id=notes layout=prose -->
<!-- resume:field heading -->
Notes
<!-- resume:field body -->
### Notes

First line
Second line

3. Third item
4. Fourth item
<!-- resume:endsection -->
<!-- resume:section id=tools layout=skills -->
<!-- resume:field heading -->
Tools
<!-- resume:field body -->
**Languages:** Python
<!-- resume:endsection -->
""".replace("First line\n", "First line  \n")
        document = self.document(HEADER + source)
        self.assertEqual(document.find(".//section/h3").get("id"), "notes-1")
        self.assertEqual(document.find(".//ol").get("start"), "3")
        self.assertEqual(len(document.findall(".//ol/li")), 2)
        self.assertIsNotNone(document.find(".//section/p/br"))
        self.assertEqual(document.find(".//section[@class='tools']/p/strong").text, "Languages:")


if __name__ == "__main__":
    unittest.main()
