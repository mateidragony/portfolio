from pathlib import Path
import unittest

from resume_parser import ResumeParseError, parse_resume
from resume_fixtures import HEADER, section


class ResumeParserTests(unittest.TestCase):
    def test_repository_resume_annotations(self):
        path = Path(__file__).resolve().parents[1] / "resume.md"
        resume = parse_resume(path.read_text(encoding="utf-8"), source=str(path))
        self.assertEqual([item.id for item in resume.sections], ["education", "experience", "projects", "technical-skills"])
        education, experience, projects, skills = resume.sections
        self.assertEqual([len(item.entries) for item in resume.sections], [2, 3, 2, 0])
        self.assertEqual([item.layout for item in resume.sections], ["entries", "entries", "entries", "skills"])

        def walk(nodes):
            for node in nodes:
                yield node
                yield from walk(node.get("children", []))

        def text(value):
            return " ".join("".join(node.get("text", "") for node in walk(value.nodes)).split())

        self.assertEqual(text(resume.header.fields["name"]), "Mat&#233;i Cloteaux")
        self.assertEqual([text(entry.fields["title-right"]) for entry in education.entries], ["May 2026", "May 2025"])
        self.assertEqual([text(entry.fields["subtitle-right"]) for entry in education.entries], ["GPA: 3.95/4.0", "GPA: 4.0/4.0"])
        self.assertTrue(all(entry.body_style == "footnote" for entry in education.entries))
        self.assertEqual([text(entry.fields["body"]) for entry in education.entries], ["Specialization: Programming Languages", "Minors: Mathematics, Informatics"])
        self.assertEqual([text(entry.fields["title-left"]) for entry in experience.entries], [
            "Managing Editor of Digital", "TechStart Intern - Cloud Engineering", "TechStart Intern - Data Applications",
        ])
        self.assertEqual([text(entry.fields["subtitle-right"]) for entry in experience.entries], ["Bloomington, IN", "Indianapolis, IN", "Portsmouth, NH"])
        self.assertTrue(all(entry.style == "project" for entry in projects.entries))
        self.assertEqual([text(entry.fields["title-left"]) for entry in projects.entries], [
            "Deduce | Python, JavaScript, HTML, CSS", "Mega Puzzle | HTML, CSS, JavaScript, Bootstrap, Cloudflare",
        ])
        self.assertEqual([len(entry.fields["body"].nodes[0]["children"]) for entry in experience.entries + projects.entries], [3, 4, 4, 2, 3])
        self.assertEqual(len(skills.fields["body"].nodes), 5)

        fields = list(resume.header.fields.values())
        for item in resume.sections:
            fields.extend(item.fields.values())
            for entry in item.entries:
                fields.extend(entry.fields.values())
        nodes = [node for value in fields for node in walk(value.nodes)]
        self.assertEqual({node["link"] for node in nodes if node["type"] == "link"}, {
            "mailto:matei.cloteaux@gmail.com",
            "https://www.linkedin.com/in/matei-cloteaux",
            "https://www.github.com/mateidragony",
            "https://github.com/jsiek/deduce",
            "https://github.com/Luddy-LLC/MegaPuzzle2024",
        })
        visible = " ".join(text(value) for value in fields)
        self.assertNotIn("Courses:", visible)
        self.assertNotIn("Undergraduate Instructor", visible)
        self.assertTrue(all(node["type"] not in {"resume_marker", "block_html", "inline_html"} for node in nodes))

    def test_explicit_fields_preserve_content_and_locations(self):
        resume = parse_resume(HEADER + section(), source="sample.md")
        self.assertEqual(resume.header.line, 1)
        self.assertEqual(resume.header.fields["name"].line, 2)
        self.assertEqual(resume.header.fields["name"].nodes[0]["children"][0]["text"], "Mat&#233;i Cloteaux")
        education = resume.sections[0]
        self.assertEqual((education.id, education.layout), ("education", "entries"))
        entry = education.entries[0]
        self.assertEqual((entry.style, entry.body_style), ("subheading", "footnote"))
        self.assertEqual(set(entry.fields), {"title-left", "title-right", "subtitle-left", "subtitle-right", "body"})
        self.assertEqual(entry.fields["title-left"].nodes[0]["children"][0]["type"], "strong")

    def test_sections_and_header_can_be_reordered(self):
        resume = parse_resume(section("research", "Selected Research") + HEADER + section("work", "Work"))
        self.assertEqual([item.id for item in resume.sections], ["research", "work"])
        self.assertEqual(resume.sections[0].fields["heading"].nodes[0]["children"][0]["text"], "Selected Research")

    def test_optional_sections_and_contacts(self):
        resume = parse_resume("<!-- resume:header -->\n<!-- resume:field name -->\nName\n<!-- resume:endheader -->\n")
        self.assertEqual(resume.sections, [])
        self.assertEqual(set(resume.header.fields), {"name"})

    def test_field_order_and_literal_pipes_do_not_define_structure(self):
        entry = """<!-- resume:entry style=project -->
<!-- resume:field title-right -->
2026 | present
<!-- resume:field title-left -->
Not bold | **[Project](https://example.com)** | *Python*
<!-- resume:endentry -->
"""
        result = parse_resume(HEADER + section(entry=entry)).sections[0].entries[0]
        self.assertEqual(result.style, "project")
        self.assertEqual(result.fields["title-right"].nodes[0]["children"][0]["text"], "2026 | present")
        self.assertEqual(result.fields["title-left"].nodes[0]["children"][1]["children"][0]["type"], "link")

    def test_optional_entry_fields(self):
        entry = "<!-- resume:entry -->\n<!-- resume:field title-left -->\nOnly title\n<!-- resume:endentry -->\n"
        result = parse_resume(HEADER + section(entry=entry)).sections[0].entries[0]
        self.assertEqual(set(result.fields), {"title-left"})

    def test_wrapped_bullets_entities_and_inline_code_remain_markdown(self):
        entry = """<!-- resume:entry -->
<!-- resume:field title-left -->
Title
<!-- resume:field body -->
- first line
  second &lt; &#42;literal&#42; with `code_value`
- **bold *and italic*** [link](https://example.com)
<!-- resume:endentry -->
"""
        body = parse_resume(HEADER + section(entry=entry)).sections[0].entries[0].fields["body"].nodes
        self.assertEqual(body[0]["type"], "list")
        children = body[0]["children"][0]["children"][0]["children"]
        self.assertIn("first line\nsecond &lt; &#42;literal&#42;", children[0]["text"])
        self.assertEqual(children[1], {"type": "codespan", "text": "code_value"})

    def test_custom_prose_and_skills_sections(self):
        for layout, body in [("prose", "A paragraph.\n\n- An item"), ("skills", "**Languages:** Python\n\n**Tools:** Git")]:
            with self.subTest(layout=layout):
                source = f"""<!-- resume:section id=custom layout={layout} -->
<!-- resume:field body -->
{body}
<!-- resume:field heading -->
Custom heading without hashes
<!-- resume:endsection -->
"""
                result = parse_resume(HEADER + source).sections[0]
                self.assertEqual(result.layout, layout)
                self.assertEqual(len(result.fields["body"].nodes), 2)

    def test_comments_are_hidden_even_inside_fields(self):
        source = HEADER.replace("# Mat&#233;i Cloteaux", "<!-- ordinary comment -->\n# Mat&#233;i <!-- inline note --> Cloteaux")
        source += "<!-- inactive content\nresume:section id=hidden\n**Not an entry**\n-->\n"
        result = parse_resume(source)
        self.assertEqual(result.sections, [])
        self.assertNotIn("inline_html", repr(result.header.fields["name"].nodes))

    def test_reference_links_resolve_across_fields(self):
        source = HEADER.replace("[Email](mailto:matei@example.com)", "[Email][address]")
        source += "\n[address]: mailto:matei@example.com\n"
        contacts = parse_resume(source).header.fields["contacts"].nodes
        self.assertEqual(contacts[0]["children"][0]["link"], "mailto:matei@example.com")

    def test_crlf_and_adjacent_directive_lines(self):
        self.assertEqual(parse_resume(HEADER.replace("\n", "\r\n")).header.fields["name"].line, 2)

    def test_empty_looking_fields_are_rejected(self):
        for name in ["#", "# <!-- note -->", "&#32;", "&#160;", "<!-- note -->"]:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ResumeParseError, "field must not be empty"):
                    parse_resume(HEADER.replace("# Mat&#233;i Cloteaux", name))

    def test_hard_breaks_and_ordered_lists_are_preserved(self):
        source = """<!-- resume:section id=notes layout=prose -->
<!-- resume:field heading -->
Notes
<!-- resume:field body -->
First line  
Second line

3. Third item
4. Fourth item
<!-- resume:endsection -->
"""
        body = parse_resume(HEADER + source).sections[0].fields["body"].nodes
        self.assertIn({"type": "linebreak"}, body[0]["children"])
        self.assertTrue(body[1]["ordered"])
        self.assertEqual(body[1]["start"], 3)

    def test_quoted_attributes(self):
        result = parse_resume(HEADER + section().replace("id=education", 'id="education"'))
        self.assertEqual(result.sections[0].id, "education")

    def test_invalid_markup_reports_context(self):
        cases = [
            ("<!-- resume:unknown -->\n", "unknown directive"),
            ("<!-- resume: -->\n", "empty directive"),
            ('<!-- resume:section id="unclosed -->\n', "invalid directive"),
            ("<!-- resume:section\nid=education -->\n", "fit on one line"),
            ("<!-- resume:header extra=x -->\n", "invalid attribute"),
            ("<!-- resume:field name -->\nName\n", "field outside"),
            (HEADER.replace("resume:field name", "resume:field name extra"), "exactly one name"),
            ("<!-- resume:endheader -->\n", "without an open header"),
            ("<!-- resume:endsection -->\n", "requires a section"),
            ("<!-- resume:endentry -->\n", "without an open entry"),
            (HEADER + HEADER, "exactly once"),
            (HEADER + section() + section(), "duplicate section id"),
            (HEADER + section().replace("id=education", "id=Bad_ID"), "hyphen-separated id"),
            (HEADER + section().replace("layout=entries", "layout=unknown"), "unknown section layout"),
            (HEADER + section().replace("layout=entries", "layout=entries layout=prose"), "duplicate attribute"),
            (HEADER + section().replace("style=footnote", "style=unknown"), "unknown body style"),
            (HEADER + section().replace("body-style=footnote", "style=unknown"), "unknown entry style"),
            (HEADER + section().replace("<!-- resume:endentry -->", ""), "no open entry"),
            (HEADER.replace("<!-- resume:endheader -->", ""), "unclosed container"),
            (HEADER.replace("<!-- resume:field name -->", "<!-- resume:field wrong -->"), "unknown field"),
            (HEADER.replace("<!-- resume:field contacts -->", "<!-- resume:field name -->"), "duplicate field"),
            (HEADER.replace("# Mat&#233;i Cloteaux", ""), "field must not be empty"),
            (HEADER.replace("# Mat&#233;i Cloteaux", "One\n\nTwo"), "single heading or paragraph"),
            (HEADER.replace("[Email](mailto:matei@example.com)", "Not a link"), "only links"),
            (HEADER + "Unmarked content\n", "explicit field"),
            ("", "missing header"),
        ]
        for text, expected in cases:
            with self.subTest(expected=expected, text=text):
                with self.assertRaisesRegex(ResumeParseError, expected) as caught:
                    parse_resume(text, source="broken.md")
                self.assertRegex(str(caught.exception), r"broken\.md:\d+:")

    def test_error_has_exact_directive_line_and_field_context(self):
        source = "\n\n" + HEADER + section().replace("<!-- resume:field title-right -->", "<!-- resume:field bad -->")
        expected_line = source[:source.index("<!-- resume:field bad -->")].count("\n") + 1
        with self.assertRaisesRegex(ResumeParseError, rf"broken.md:{expected_line}: unknown field.*section 'education'.*entry"):
            parse_resume(source, source="broken.md")

    def test_required_fields_and_scope_errors(self):
        cases = [
            ("<!-- resume:header -->\n<!-- resume:endheader -->\n", "missing required field 'name'"),
            (HEADER + section(entry="<!-- resume:entry -->\n<!-- resume:endentry -->\n"), "missing required field 'title-left'"),
            (HEADER + section().replace("<!-- resume:field subtitle-left -->\nMaster of Science in Computer Science\n", ""), "missing required field 'subtitle-left'"),
            (HEADER + section().replace("<!-- resume:entry body-style=footnote -->", "<!-- resume:entry style=project -->"), "unknown field 'subtitle-left'"),
            (HEADER + "<!-- resume:section id=x layout=skills -->\n<!-- resume:entry -->\n", "requires an entries section"),
            (HEADER + "<!-- resume:section id=x -->\n<!-- resume:endsection -->\n", "missing required field 'heading'"),
            (HEADER + section().replace("<!-- resume:entry body-style=footnote -->", "<!-- resume:entry -->\n<!-- resume:entry -->"), "cannot be nested"),
            (HEADER + section().replace("<!-- resume:field heading -->", "<!-- resume:section id=nested -->"), "must be top level"),
            (HEADER + "<!-- resume:section id=skills layout=skills -->\n<!-- resume:field heading -->\nSkills\n<!-- resume:endsection -->\n", "missing required field 'body'"),
        ]
        for source, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ResumeParseError, expected):
                    parse_resume(source)

    def test_skill_layout_rejects_nonparagraph_body(self):
        source = """<!-- resume:section id=skills layout=skills -->
<!-- resume:field heading -->
Skills
<!-- resume:field body -->
- Python
<!-- resume:endsection -->
"""
        with self.assertRaisesRegex(ResumeParseError, "skills body must contain paragraphs"):
            parse_resume(HEADER + source)

    def test_unsupported_markdown_and_embedded_directives_do_not_execute(self):
        for body, expected in [
            ("```text\n<!-- resume:endheader -->\n```", "block_code"),
            ("    <!-- resume:endheader -->", "block_code"),
            ("> A quote", "block_quote"),
            ("<div>Raw HTML</div>", "block_html"),
            ("![image](image.png)", "image"),
            ("- outer\n  - inner", "nested lists"),
            ("Text <!-- resume:endheader --> inline", "standalone top-level"),
        ]:
            with self.subTest(body=body):
                entry = f"<!-- resume:entry -->\n<!-- resume:field title-left -->\nTitle\n<!-- resume:field body -->\n{body}\n<!-- resume:endentry -->\n"
                with self.assertRaisesRegex(ResumeParseError, expected):
                    parse_resume(HEADER + section(entry=entry))


if __name__ == "__main__":
    unittest.main()
