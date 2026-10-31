HEADER = """<!-- resume:header -->
<!-- resume:field name -->
# Mat&#233;i Cloteaux
<!-- resume:field contacts -->
[Email](mailto:matei@example.com)
[Site](https://example.com?a=1&b=2#contact)
<!-- resume:endheader -->
"""


def section(identifier="education", heading="Education", entry=None):
    if entry is None:
        entry = """<!-- resume:entry body-style=footnote -->
<!-- resume:field title-left -->
**Indiana University,** Bloomington, IN
<!-- resume:field title-right -->
May 2026
<!-- resume:field subtitle-left -->
Master of Science in Computer Science
<!-- resume:field subtitle-right -->
GPA: 3.95/4.0
<!-- resume:field body -->
Specialization: Programming Languages
<!-- resume:endentry -->
"""
    return f"""<!-- resume:section id={identifier} layout=entries -->
<!-- resume:field heading -->
## {heading}
{entry}<!-- resume:endsection -->
"""
