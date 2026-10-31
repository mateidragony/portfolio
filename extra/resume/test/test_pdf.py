from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from gen_latex import render_latex
from publish_resume import BASENAME, LATEST_FILENAME, STATE_FILENAME, publish_resume
from resume_parser import parse_resume
from resume_fixtures import HEADER, section


class ResumePDFTests(unittest.TestCase):
    def render(self, source, template=None):
        if template is None:
            path = Path(__file__).resolve().parents[1] / "latex" / "template.tex"
            template = path.read_text(encoding="utf-8")
        return render_latex(parse_resume(source), template)

    @unittest.skipUnless(shutil.which("pdflatex"), "pdflatex is not installed")
    def test_generated_edge_cases_compile(self):
        entry = """<!-- resume:entry -->
<!-- resume:field title-left -->
First line
Second line
<!-- resume:endentry -->
<!-- resume:entry -->
<!-- resume:field title-left -->
**[A &amp; B](https://example.com/a_b/~user?q=50%25&x=1#frag)**
<!-- resume:field subtitle-left -->
Optional subtitle without a right column
<!-- resume:field body -->
Text and `&%$#_{}~^<>|` with **bold and *italic* text**.

- Wrapped text on the first
  and second line.
<!-- resume:endentry -->
""".replace("First line\n", "First line  \n")
        custom = """<!-- resume:section id=notes layout=prose -->
<!-- resume:field heading -->
Notes
<!-- resume:field body -->
### Detail

3. Third item
4. Fourth item
<!-- resume:endsection -->
"""
        with tempfile.TemporaryDirectory(prefix="resume-latex-test-") as directory:
            source = Path(directory) / "edge-cases.tex"
            source.write_text(self.render(HEADER + section(entry=entry) + custom), encoding="utf-8")
            result = subprocess.run(
                [shutil.which("pdflatex"), "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", source.name],
                cwd=directory, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr)
            self.assertTrue(source.with_suffix(".pdf").exists())


class ResumePublishTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="resume-publish-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        (self.directory / "resume.md").write_text(HEADER + section(), encoding="utf-8")
        (self.directory / "latex").mkdir()
        template = Path(__file__).resolve().parents[1] / "latex" / "template.tex"
        shutil.copyfile(template, self.directory / "latex" / "template.tex")
        css = self.directory / "html" / "css"
        css.mkdir(parents=True)
        (css / "style.css").write_text("header { h1 { font-size: 40px; } }", encoding="utf-8")
        (css / "normalize.css").write_text("body { margin: 0; }", encoding="utf-8")
        self.compiler_patcher = mock.patch("publish_resume._compile_pdf", side_effect=self.compile_pdf)
        self.compiler = self.compiler_patcher.start()
        self.addCleanup(self.compiler_patcher.stop)
        self.today = date(2026, 10, 31)

    def compile_pdf(self, directory, latex):
        pdf = directory / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4\n" + hashlib.sha256(latex.encode("utf-8")).digest())
        return pdf

    def publish(self, publication_date=None):
        return publish_resume(self.directory, publication_date or self.today)

    def change_resume(self):
        path = self.directory / "resume.md"
        path.write_text(path.read_text(encoding="utf-8").replace("May 2026", "June 2026"), encoding="utf-8")

    def test_first_publication_creates_dated_pdf_and_stable_download(self):
        dated = self.publish()
        self.assertEqual(dated.name, f"{BASENAME}-2026-10-31.pdf")
        self.assertEqual(dated.read_bytes(), (self.directory / LATEST_FILENAME).read_bytes())
        state = json.loads((self.directory / STATE_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(state["current"], dated.name)
        self.assertFalse((self.directory / "archive").exists())

    def test_unchanged_publication_does_not_compile_rename_or_touch_files(self):
        self.publish()
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.directory.iterdir() if path.is_file()}
        self.assertIsNone(self.publish(date(2026, 11, 1)))
        after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.directory.iterdir() if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(self.compiler.call_count, 1)

    def test_changed_publication_archives_only_previous_dated_copy(self):
        first = self.publish()
        original = first.read_bytes()
        self.change_resume()
        second = self.publish(date(2026, 11, 1))
        self.assertFalse(first.exists())
        self.assertEqual((self.directory / "archive" / first.name).read_bytes(), original)
        self.assertEqual(second.read_bytes(), (self.directory / LATEST_FILENAME).read_bytes())
        self.assertEqual(len(list(self.directory.glob(f"{BASENAME}-*.pdf"))), 1)
        self.assertEqual(len(list((self.directory / "archive").glob("*.pdf"))), 1)

    def test_initial_undated_copy_is_archived_without_losing_bytes(self):
        legacy = b"%PDF-1.4\nprevious publication"
        (self.directory / LATEST_FILENAME).write_bytes(legacy)
        dated = self.publish()
        self.assertEqual((self.directory / "archive" / LATEST_FILENAME).read_bytes(), legacy)
        self.assertEqual((self.directory / LATEST_FILENAME).read_bytes(), dated.read_bytes())

    def test_same_day_revisions_do_not_overwrite_archive_collisions(self):
        first = self.publish()
        self.change_resume()
        second = self.publish()
        self.assertEqual(second.name, f"{BASENAME}-2026-10-31-02.pdf")
        path = self.directory / "resume.md"
        path.write_text(path.read_text(encoding="utf-8").replace("June 2026", "July 2026"), encoding="utf-8")
        third = self.publish()
        self.assertEqual(third.name, f"{BASENAME}-2026-10-31-03.pdf")
        self.assertTrue((self.directory / "archive" / first.name).exists())
        self.assertTrue((self.directory / "archive" / second.name).exists())

    def test_markdown_comments_and_wrapping_changes_do_not_publish(self):
        self.publish()
        source = self.directory / "resume.md"
        text = source.read_text(encoding="utf-8")
        text = "<!-- Draft note -->\n\n" + text.replace("Master of Science in Computer Science", "Master of Science\nin Computer Science")
        source.write_text(text, encoding="utf-8")
        self.assertIsNone(self.publish())
        self.assertEqual(self.compiler.call_count, 1)

    def test_layout_changes_are_publication_changes(self):
        self.publish()
        css = self.directory / "html" / "css" / "style.css"
        css.write_text("header { h1 { font-size: 42px; } }", encoding="utf-8")
        self.assertIsNotNone(self.publish())
        template = self.directory / "latex" / "template.tex"
        template.write_text(template.read_text(encoding="utf-8").replace("11pt", "12pt"), encoding="utf-8")
        self.assertIsNotNone(self.publish())
        self.assertEqual(self.compiler.call_count, 3)

    def test_compilation_failure_preserves_publication_and_metadata(self):
        self.publish()
        before = {path.name: path.read_bytes() for path in self.directory.iterdir() if path.is_file()}
        self.change_resume()
        expected = dict(before)
        expected["resume.md"] = (self.directory / "resume.md").read_bytes()
        self.compiler.side_effect = RuntimeError("compiler failed")
        with self.assertRaisesRegex(RuntimeError, "compiler failed"):
            self.publish()
        after = {path.name: path.read_bytes() for path in self.directory.iterdir() if path.is_file()}
        self.assertEqual(expected, after)
        self.assertFalse((self.directory / "archive").exists())
        self.assertFalse(list(self.directory.glob(".resume-publish-*")))

    def test_metadata_commit_failure_rolls_back_files(self):
        first = self.publish()
        original = first.read_bytes()
        state = (self.directory / STATE_FILENAME).read_bytes()
        self.change_resume()
        replace = Path.replace

        def fail_metadata(path, target):
            if path.name == STATE_FILENAME:
                raise OSError("metadata write failed")
            return replace(path, target)

        with mock.patch.object(Path, "replace", fail_metadata):
            with self.assertRaisesRegex(OSError, "metadata write failed"):
                self.publish()
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual((self.directory / LATEST_FILENAME).read_bytes(), original)
        self.assertEqual((self.directory / STATE_FILENAME).read_bytes(), state)
        self.assertEqual(len(list(self.directory.glob(f"{BASENAME}-*.pdf"))), 1)
        self.assertEqual(list((self.directory / "archive").iterdir()), [])

    def test_bad_metadata_and_modified_pdfs_are_not_silently_replaced(self):
        dated = self.publish()
        dated.write_bytes(b"modified outside publisher")
        with self.assertRaisesRegex(ValueError, "modified outside"):
            self.publish()
        state_path = self.directory / STATE_FILENAME
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["current"] = "../outside.pdf"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid published PDF filename"):
            self.publish()

    def test_draft_generators_do_not_publish_or_archive(self):
        dated = self.publish()
        original = dated.read_bytes()
        metadata = (self.directory / STATE_FILENAME).read_bytes()
        self.change_resume()
        scripts = Path(__file__).resolve().parents[1]
        for filename in ["gen_html.py", "gen_latex.py", "resume_parser.py"]:
            shutil.copyfile(scripts / filename, self.directory / filename)
        for filename in ["gen_html.py", "gen_latex.py"]:
            subprocess.run([sys.executable, str(self.directory / filename)], cwd=self.directory, capture_output=True, text=True, check=True)
        self.assertTrue((self.directory / "html" / "resume.html").exists())
        self.assertTrue((self.directory / "latex" / "resume.tex").exists())
        self.assertEqual(dated.read_bytes(), original)
        self.assertEqual((self.directory / LATEST_FILENAME).read_bytes(), original)
        self.assertEqual((self.directory / STATE_FILENAME).read_bytes(), metadata)
        self.assertFalse((self.directory / "archive").exists())

    def test_first_publication_failure_does_not_archive_existing_download(self):
        original = b"%PDF-1.4\nprevious resume"
        (self.directory / LATEST_FILENAME).write_bytes(original)
        self.compiler.side_effect = RuntimeError("compiler failed")
        with self.assertRaisesRegex(RuntimeError, "compiler failed"):
            self.publish()
        self.assertEqual((self.directory / LATEST_FILENAME).read_bytes(), original)
        self.assertFalse((self.directory / "archive").exists())
        self.assertFalse((self.directory / STATE_FILENAME).exists())

    def test_missing_metadata_does_not_guess_at_existing_dated_publications(self):
        self.publish()
        (self.directory / STATE_FILENAME).unlink()
        with self.assertRaisesRegex(ValueError, "metadata is missing"):
            self.publish()
        self.assertEqual(self.compiler.call_count, 1)

    def test_archive_name_collisions_preserve_existing_files(self):
        first = self.publish()
        archive = self.directory / "archive"
        archive.mkdir()
        collision = archive / first.name
        collision.write_bytes(b"older archived file")
        self.change_resume()
        self.publish(date(2026, 11, 1))
        self.assertEqual(collision.read_bytes(), b"older archived file")
        self.assertTrue((archive / f"{first.stem}-02.pdf").exists())

    @unittest.skipUnless(shutil.which("pdflatex"), "pdflatex is not installed")
    def test_real_compiler_publishes_once_and_reuses_unchanged_pdf(self):
        self.compiler_patcher.stop()
        dated = self.publish()
        self.assertTrue(dated.read_bytes().startswith(b"%PDF-"))
        self.assertEqual(dated.read_bytes(), (self.directory / LATEST_FILENAME).read_bytes())
        before = dated.stat().st_mtime_ns
        self.assertIsNone(self.publish(date(2026, 11, 1)))
        self.assertEqual(dated.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
