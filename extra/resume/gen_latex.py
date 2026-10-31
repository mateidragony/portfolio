"""Render annotated resume Markdown as LaTeX using the shared Mistune parser."""

import argparse
from html import unescape
from pathlib import Path
import re
from urllib.parse import quote

from resume_parser import Entry, Field, Node, Resume, parse_resume


# Margins in inches
TOP_MARGIN = "0.3in"
BOTTOM_MARGIN = "0.3in"
LEFT_MARGIN = "0.5in"
RIGHT_MARGIN = "0.5in"


LATEX_ESCAPES = {
	"\\": r"\textbackslash{}",
	"&": r"\&",
	"%": r"\%",
	"$": r"\$",
	"#": r"\#",
	"_": r"\_",
	"{": r"\{",
	"}": r"\}",
	"~": r"\textasciitilde{}",
	"^": r"\textasciicircum{}",
	"<": r"\textless{}",
	">": r"\textgreater{}",
	"|": r"\textbar{}",
}


def escape_latex(text: str) -> str:
	return "".join(LATEX_ESCAPES.get(char, char) for char in text)


def escape_latex_url(url: str) -> str:
	url = quote(unescape(url), safe=":/?#[]@!$&'()*+,;=%-._~")
	return "".join("\\" + char if char in "&%$#_" else char for char in url)


class _ResumeLaTeXRenderer:
	def render_inline(self, nodes: list[Node], underline_links: bool = False) -> str:
		result = []
		for node in nodes:
			kind = node["type"]
			if kind == "text":
				result.append(escape_latex(unescape(node["text"]).replace("\n", " ")))
			elif kind == "codespan":
				result.append(f"\\texttt{{{escape_latex(node['text'])}}}")
			elif kind == "linebreak":
				result.append("\\\\\n")
			elif kind in {"strong", "emphasis", "link"}:
				children = self.render_inline(node["children"], underline_links)
				if kind == "link":
					url = escape_latex_url(node["link"])
					label = f"\\underline{{{children}}}" if underline_links else children
					result.append(f"\\href{{{url}}}{{{label}}}")
				else:
					command = "textbf" if kind == "strong" else "emph"
					result.append(f"\\{command}{{{children}}}")
			else:
				raise ValueError(f"unsupported inline Markdown node {kind!r}")
		return "".join(result)

	def render_field(self, value: Field | None, align: str = "l") -> str:
		if value is None:
			return ""
		text = self.render_inline(value.nodes[0]["children"])
		return f"\\shortstack[{align}]{{{text}}}" if "\\\\\n" in text else text

	def render_blocks(self, nodes: list[Node], entry_body: bool = False) -> str:
		result = []
		for node in nodes:
			kind = node["type"]
			if kind in {"paragraph", "block_text"}:
				result.append(self.render_inline(node["children"]) + ("\n\n" if kind == "paragraph" else ""))
			elif kind == "heading":
				result.append(f"\\textbf{{{self.render_inline(node['children'])}}}\\par\n")
			elif kind == "list":
				compact = entry_body and not node["ordered"]
				if compact:
					result.append("\\resumeItemListStart\n")
				else:
					environment = "enumerate" if node["ordered"] else "itemize"
					options = "leftmargin=0.3in"
					if node["ordered"]:
						options += f",start={node.get('start', 1)}"
					result.append(f"\\begin{{{environment}}}[{options}]\n")
				for item in node["children"]:
					text = self.render_blocks(item["children"]).strip()
					result.append(f"\\resumeItem{{{text}}}\n" if compact else f"\\item {text}\n")
				result.append("\\resumeItemListEnd\n" if compact else f"\\end{{{environment}}}\n")
			else:
				raise ValueError(f"unsupported block Markdown node {kind!r}")
		return "".join(result)

	def render_entry(self, entry: Entry) -> str:
		left = self.render_field(entry.fields["title-left"])
		right = self.render_field(entry.fields.get("title-right"), "r")
		subtitle = "subtitle-left" in entry.fields
		if entry.style == "project":
			latex = f"\\resumeProjectHeading\n{{{left}}}{{{right}}}\n"
		elif subtitle:
			sub_left = self.render_field(entry.fields["subtitle-left"])
			sub_right = self.render_field(entry.fields.get("subtitle-right"), "r")
			latex = f"\\resumeSubheading\n{{{left}}}{{{right}}}\n{{{sub_left}}}{{{sub_right}}}\n"
		else:
			latex = f"\\resumeHeading\n{{{left}}}{{{right}}}\n"
		body = entry.fields.get("body")
		if body is not None:
			spacing = -19 if subtitle else -18
			latex += f"\\vspace{{{spacing}pt}}\n"
			content = self.render_blocks(body.nodes, entry_body=True).strip()
			if entry.body_style == "footnote":
				latex += f"\n{{\\footnotesize {content}}}\n\\vspace{{-4pt}}\n"
			else:
				latex += f"{{\\small {content}}}\n"
		return latex

	def render_sections(self, resume: Resume) -> str:
		parts = []
		for section in resume.sections:
			heading = self.render_inline(section.fields["heading"].nodes[0]["children"])
			parts.append(f"\\section{{{heading}}}\n")
			if section.layout == "entries":
				if section.entries:
					parts.append("\\resumeSubHeadingListStart\n")
					parts.extend(self.render_entry(entry) for entry in section.entries)
					if section.entries[-1].body_style == "footnote":
						parts.append("\\vspace{-4pt}\n")
					parts.append("\\resumeSubHeadingListEnd\n")
			elif section.layout == "skills":
				lines = [self.render_inline(node["children"]) for node in section.fields["body"].nodes]
				content = " \\\\\n".join(lines)
				parts.append("\\begin{itemize}[leftmargin=0in, label={}]\n")
				parts.append(f"\\small{{\\item{{{content}}}}}\n\\end{{itemize}}\n")
			else:
				parts.append(self.render_blocks(section.fields["body"].nodes))
			parts.append("\n")
		return "".join(parts)


def render_latex(resume: Resume, template: str) -> str:
	"""Render a validated resume without assuming section names or field order."""
	renderer = _ResumeLaTeXRenderer()
	contacts = resume.header.fields.get("contacts")
	links = []
	if contacts is not None:
		for paragraph in contacts.nodes:
			links.extend(renderer.render_inline([node], underline_links=True) for node in paragraph["children"] if node["type"] == "link")
	values = {
		"TOP_MARGIN": TOP_MARGIN,
		"BOTTOM_MARGIN": BOTTOM_MARGIN,
		"LEFT_MARGIN": LEFT_MARGIN,
		"RIGHT_MARGIN": RIGHT_MARGIN,
		"NAME": renderer.render_field(resume.header.fields["name"], "c"),
		"LINKS_LATEX": " $|$ ".join(links),
		"SECTIONS_LATEX": renderer.render_sections(resume),
	}

	def replace(match):
		name = match.group(1)
		if name not in values:
			raise ValueError(f"unknown LaTeX template placeholder {name!r}")
		return values[name]

	return re.sub(r"<<([^<>]+)>>", replace, template)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.parse_args()
	directory = Path(__file__).resolve().parent
	source = directory / "resume.md"
	print("Reading markdown")
	resume = parse_resume(source.read_text(encoding="utf-8"), source=str(source))
	template = (directory / "latex" / "template.tex").read_text(encoding="utf-8")
	latex = render_latex(resume, template)
	print("Writing LaTeX")
	(directory / "latex" / "resume.tex").write_text(latex, encoding="utf-8")


if __name__ == "__main__":
	main()

