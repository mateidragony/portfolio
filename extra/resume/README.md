# 📄 Resume

[resume.md](resume.md) is the shared source for the
HTML and LaTeX resumes.

[resume-archive.md](resume-archive.md): holds previous resume entries removed from `resume.md`.

## Drafts and Publication

Run the following commands to generate draft previews:

```sh
python gen_html.py
python gen_latex.py
```

When a version is ready to publish, explicitly run:

```sh
python publish_resume.py
```

[publish_resume.py](publish_resume.py) builds the PDF independently of the draft
files. The date in its filename is the local publication date, not the date of
each preview build. After several publications, the directory might contain:

```text
MateiCloteauxResume.pdf
MateiCloteauxResume-2026-10-31.pdf
published-resume.json
archive/
	MateiCloteauxResume-2026-10-20.pdf
```

[MateiCloteauxResume.pdf](MateiCloteauxResume.pdf) remains a stable download of the
latest published version so the website's existing links keep working. There is
also one dated current PDF alongside it; previous dated PDFs move into `archive/`.
Multiple changed publications on one day use suffixes such as `-02` and `-03`.
Archive filename collisions also receive a suffix rather than overwriting a file.

The publisher fingerprints rendered HTML and LaTeX plus the local CSS files, not
PDF bytes or build timestamps. Markdown comments and ordinary source-line wrapping
do not count as changes. Changes to content, formatting, section structure,
rendered template output, or CSS inputs can create a new publication. CSS-file
edits are counted conservatively, including changes to CSS comments.

An unchanged publication does not compile again, rename files, or modify published
PDFs or metadata. A changed publication compiles twice in a temporary directory
before moving any previous PDF. Compilation failures leave the existing
publication untouched; ordinary file-update failures attempt to restore it.

### GitHub Actions

The [Pages deployment](../../.github/workflows/deploy-static.yml) and
[manual resume workflow](../../.github/workflows/generate-resume.yml) use a
[shared action](../../.github/actions/generate-resume/action.yml) to install
Python and LaTeX, run all tests, generate drafts, and publish changed PDFs.
Pages deployment uploads the site only after those steps succeed.

Both workflows commit generated HTML, LaTeX, current PDFs, archived PDFs, and
publication metadata back to the triggering branch. This preserves history and
change detection between CI runs. Unchanged generated outputs produce no commit;
bot commits use `[skip ci]` to avoid redundant builds. The workflows share the
`pages` concurrency group and check out the current branch tip.

## Annotated Markdown

Put each directive comment on its own line. A field owns all Markdown until
the next directive. Close headers, entries, and sections explicitly:

```markdown
<!-- resume:header -->
<!-- resume:field name -->
# Name
<!-- resume:field contacts -->
[Email](mailto:name@example.com)
<!-- resume:endheader -->

<!-- resume:section id=work layout=entries -->
<!-- resume:field heading -->
## Selected Work
<!-- resume:entry style=subheading -->
<!-- resume:field title-left -->
**Position**
<!-- resume:field title-right -->
2024 -- 2026
<!-- resume:field subtitle-left -->
Organization
<!-- resume:field subtitle-right -->
Location
<!-- resume:field body -->
- A contribution with *emphasis* and a [link](https://example.com).
<!-- resume:endentry -->
<!-- resume:endsection -->

<!-- resume:section id=summary layout=prose -->
<!-- resume:field heading -->
## Summary
<!-- resume:field body -->
A paragraph of ordinary Markdown.
<!-- resume:endsection -->
```

Exactly one header is required. It may appear anywhere in the source but renders
at the top. Sections render in source order and may be renamed, reordered, added,
or omitted. Their IDs must be unique lowercase words separated by hyphens, such
as `technical-skills`. IDs provide HTML hooks independently of the visible titles.

| Container | Fields |
| --- | --- |
| Header | Required `name`; optional `contacts`, containing only Markdown links and whitespace. |
| Entries section | Required `heading`; zero or more entries. |
| Skills or prose section | Required `heading` and `body`; no entry wrappers. |
| Entry | Required `title-left`; optional `title-right` and `body`. Subheading entries also allow optional `subtitle-left` and `subtitle-right`; a right subtitle requires a left subtitle. |

`name` and `heading` accept one Markdown heading or paragraph. Column fields
accept one paragraph.

Section `layout` defaults to `entries`. The supported layouts are:

- `entries`: structured heading rows with optional body content.
- `skills`: paragraphs, such as `**Languages:** Python, JavaScript`.
- `prose`: paragraphs, headings, and flat lists.

Entry `style` defaults to `subheading`. Use `project` for a single-row heading
without subtitles. For example, its `title-left` can contain
`**[Project](https://example.com)** | *Python, JavaScript*`. `body-style=footnote` provides compact LaTeX body
text, as used for education; its default is `normal`. Layouts and entry styles
are reusable in any section, regardless of its ID or title.

Malformed directives, duplicate fields or IDs, missing required fields, and
unclosed containers raise errors identifying the source, line, and current
structural context. Validation finishes before a generator overwrites its output.

### Tests

From the resume directory, run the tests with:

```sh
python -m unittest discover -s test -p 'test*.py' -v
```

The suite is separated by concern:

- [test/test_parser.py](test/test_parser.py): Markdown directives, fields, and validation.
- [test/test_html.py](test/test_html.py): HTML structure, formatting, and links.
- [test/test_latex.py](test/test_latex.py): LaTeX rendering, escaping, and templates.
- [test/test_pdf.py](test/test_pdf.py): PDF compilation, publication, and archives.

[test/resume_fixtures.py](test/resume_fixtures.py) contains shared Markdown fixtures
and is not discovered as a test module. To run one group, use its filename:

```sh
python -m unittest discover -s test -p 'test_pdf.py' -v
```

Tests that compile PDFs skip automatically when `pdflatex` is unavailable.
