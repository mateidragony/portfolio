from pathlib import Path
import unittest

from gen_latex import escape_latex, escape_latex_url, render_latex
from resume_parser import parse_resume
from resume_fixtures import HEADER, section


class ResumeLaTeXTests(unittest.TestCase):
    def render(self, source, template=None):
        if template is None:
            path = Path(__file__).resolve().parents[1] / "latex" / "template.tex"
            template = path.read_text(encoding="utf-8")
        return render_latex(parse_resume(source), template)

    def test_repository_latex_structure_and_content(self):
        source = Path(__file__).resolve().parents[1] / "resume.md"
        latex = self.render(source.read_text(encoding="utf-8"))
        self.assertNotIn("<<", latex)
        self.assertNotIn("resume:", latex)
        self.assertIn("Mat\u00e9i Cloteaux", latex)
        self.assertEqual(latex.count("\\resumeSubheading\n"), 5)
        self.assertEqual(latex.count("\\resumeProjectHeading\n"), 2)
        document = latex.split(r"\begin{document}", 1)[1]
        self.assertEqual(document.count("\\resumeItem{"), 16)
        self.assertEqual(latex.count("\\href{"), 5)
        self.assertIn(r"{\textbf{Indiana University,} Bloomington, IN}{May 2026}", latex)
        self.assertNotIn("University,,", latex)
        self.assertIn("using AWS services", latex)
        self.assertIn("to expanded Deduce", latex)
        self.assertIn(r"40\%", latex)
        self.assertIn(r"\textbf{Languages:} Python", latex)
        self.assertNotIn("Courses:", latex)
        self.assertNotIn("Undergraduate Instructor", latex)
        headings = [latex.index(f"\\section{{{name}}}") for name in ["Education", "Experience", "Projects", "Technical Skills"]]
        self.assertEqual(headings, sorted(headings))

    def test_custom_sections_follow_source_order_and_display_names(self):
        source = section("research", "Research & Studies") + HEADER + section("work", "Selected Work")
        latex = self.render(source)
        self.assertLess(latex.index(r"\section{Research \& Studies}"), latex.index(r"\section{Selected Work}"))
        self.assertNotIn(r"\section{Education}", latex)

    def test_optional_header_and_entry_fields(self):
        entry = "<!-- resume:entry -->\n<!-- resume:field title-left -->\nTitle\n<!-- resume:endentry -->\n"
        latex = self.render(HEADER + section(entry=entry))
        self.assertIn("\\resumeHeading\n{Title}{}", latex)
        self.assertNotIn("\\vspace{-18pt}", latex)
        minimal = "<!-- resume:header -->\n<!-- resume:field name -->\nName\n<!-- resume:endheader -->\n"
        body = self.render(minimal).split(r"\begin{document}", 1)[1]
        self.assertNotIn(r"\href", body)
        self.assertNotIn(r"\begin{itemize}", body)

    def test_text_and_url_escaping_have_distinct_rules(self):
        self.assertEqual(escape_latex("&%$#_{}\\~^<>|"), r"\&\%\$\#\_\{\}\textbackslash{}\textasciitilde{}\textasciicircum{}\textless{}\textgreater{}\textbar{}")
        self.assertEqual(escape_latex_url("https://example.com/a_b?q=50%25&amp;x=1#frag"), r"https://example.com/a\_b?q=50\%25\&x=1\#frag")
        self.assertEqual(escape_latex_url("https://example.com/{x}^\\~"), r"https://example.com/\%7Bx\%7D\%5E\%5C~")

    def test_recursive_inline_formatting_entities_and_code(self):
        entry = """<!-- resume:entry style=project -->
<!-- resume:field title-left -->
**[Project](https://example.com/a_b?x=50%25&y=1#frag)** | *Python*
<!-- resume:field body -->
**bold**ness &lt;tag&gt; &amp; &#42;literal&#42; `&lt;code&gt;`

- **bold and *italic* text** with a wrapped
  line and 40%.
<!-- resume:endentry -->
"""
        latex = self.render(HEADER + section(entry=entry))
        self.assertIn(r"\textbf{\href{https://example.com/a\_b?x=50\%25\&y=1\#frag}{Project}} \textbar{} \emph{Python}", latex)
        self.assertIn(r"\textbf{bold}ness \textless{}tag\textgreater{} \& *literal* \texttt{\&lt;code\&gt;}", latex)
        self.assertIn(r"\textbf{bold and \emph{italic} text} with a wrapped line and 40\%.", latex)

    def test_custom_prose_skills_ordered_lists_and_hard_breaks(self):
        source = """<!-- resume:section id=notes layout=prose -->
<!-- resume:field heading -->
Notes
<!-- resume:field body -->
### Detail

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

**Tools:** Git
<!-- resume:endsection -->
""".replace("First line\n", "First line  \n")
        latex = self.render(HEADER + source)
        self.assertIn("First line\\\\\nSecond line", latex)
        self.assertIn(r"\textbf{Detail}\par", latex)
        self.assertIn(r"\begin{enumerate}[leftmargin=0.3in,start=3]", latex)
        self.assertIn(r"\item Third item", latex)
        self.assertIn("\\textbf{Languages:} Python \\\\\n\\textbf{Tools:} Git", latex)

    def test_hard_breaks_in_heading_fields_use_a_stack(self):
        entry = "<!-- resume:entry -->\n<!-- resume:field title-left -->\nFirst line  \nSecond line\n<!-- resume:endentry -->\n"
        latex = self.render(HEADER + section(entry=entry))
        self.assertIn("\\shortstack[l]{First line\\\\\nSecond line}", latex)

    def test_template_substitution_is_single_pass(self):
        source = HEADER.replace("# Mat&#233;i Cloteaux", "&lt;&lt;NAME&gt;&gt;")
        self.assertEqual(self.render(source, "<<NAME>>"), r"\textless{}\textless{}NAME\textgreater{}\textgreater{}")
        with self.assertRaisesRegex(ValueError, "unknown LaTeX template placeholder"):
            self.render(HEADER, "<<UNKNOWN>>")


if __name__ == "__main__":
    unittest.main()
