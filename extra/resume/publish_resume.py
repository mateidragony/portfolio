"""Explicitly publish a changed resume PDF and preserve previous publications."""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from gen_html import render_html
from gen_latex import render_latex
from resume_parser import parse_resume


BASENAME = "MateiCloteauxResume"
STATE_FILENAME = "published-resume.json"
LATEST_FILENAME = f"{BASENAME}.pdf"
PUBLICATION_PATTERN = re.compile(rf"{BASENAME}-\d{{4}}-\d{{2}}-\d{{2}}(?:-\d{{2,}})?\.pdf")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _publication_inputs(directory: Path) -> tuple[str, str]:
    source = directory / "resume.md"
    resume = parse_resume(source.read_text(encoding="utf-8"), source=str(source))
    template = (directory / "latex" / "template.tex").read_text(encoding="utf-8")
    latex = render_latex(resume, template)
    inputs = {
        "html": re.sub(r"\s+", " ", render_html(resume)).strip(),
        "latex": re.sub(r"\s+", " ", latex).strip(),
        "css": {
            filename: (directory / "html" / "css" / filename).read_text(encoding="utf-8")
            for filename in ["normalize.css", "style.css"]
        },
    }
    fingerprint = _sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=True).encode("utf-8"))
    return latex, fingerprint


def _load_state(directory: Path) -> dict | None:
    path = directory / STATE_FILENAME
    if path.is_symlink():
        raise ValueError("publication metadata must not be a symlink")
    if not path.exists():
        if any(directory.glob(f"{BASENAME}-*.pdf")):
            raise ValueError("dated PDFs exist but publication metadata is missing; restore the metadata first")
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("version") != 1:
        raise ValueError("unsupported publication metadata")
    filename = state.get("current", "")
    if not isinstance(filename, str) or not PUBLICATION_PATTERN.fullmatch(filename):
        raise ValueError("invalid published PDF filename in metadata")
    for key in ["fingerprint", "pdf_sha256"]:
        if not isinstance(state.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", state[key]):
            raise ValueError(f"invalid {key} in publication metadata")
    current = directory / filename
    latest = directory / LATEST_FILENAME
    for published in [current, latest]:
        if published.is_symlink() or not published.is_file():
            raise ValueError(f"published PDF is missing or is not a regular file: {published.name}")
        if _sha256(published.read_bytes()) != state["pdf_sha256"]:
            raise ValueError(f"published PDF was modified outside the publisher: {published.name}")
    return state


def _available_name(directory: Path, filename: str, other_directory: Path | None = None) -> str:
    candidate = filename
    suffix = 2
    while any((parent / candidate).exists() or (parent / candidate).is_symlink() for parent in [directory, other_directory] if parent is not None):
        path = Path(filename)
        candidate = f"{path.stem}-{suffix:02d}{path.suffix}"
        suffix += 1
    return candidate


def _compile_pdf(directory: Path, latex: str) -> Path:
    executable = shutil.which("pdflatex")
    if executable is None:
        raise RuntimeError("pdflatex is required to publish a resume; install a LaTeX distribution first")
    source = directory / "resume.tex"
    source.write_text(latex, encoding="utf-8")
    for _ in range(2):
        try:
            result = subprocess.run(
                [executable, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", source.name],
                cwd=directory, capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("LaTeX compilation timed out; published files were not changed") from error
        if result.returncode:
            raise RuntimeError("LaTeX compilation failed; published files were not changed:\n" + result.stdout[-4000:] + result.stderr)
    pdf = source.with_suffix(".pdf")
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("LaTeX did not produce a PDF; published files were not changed")
    return pdf


def publish_resume(directory: Path, publication_date: date | None = None) -> Path | None:
    """Publish changed inputs; return the dated PDF, or None when unchanged."""
    directory = directory.resolve()
    archive = directory / "archive"
    latest = directory / LATEST_FILENAME
    if archive.is_symlink() or (archive.exists() and not archive.is_dir()):
        raise ValueError("archive must be a regular directory")
    if latest.is_symlink() or (latest.exists() and not latest.is_file()):
        raise ValueError("the latest PDF must be a regular file")
    state = _load_state(directory)
    latex, fingerprint = _publication_inputs(directory)
    if state is not None and state["fingerprint"] == fingerprint:
        return None
    previous = directory / state["current"] if state is not None else latest if latest.exists() else None
    publication_date = publication_date or date.today()
    filename = _available_name(directory, f"{BASENAME}-{publication_date.isoformat()}.pdf", archive)
    destination = directory / filename
    with tempfile.TemporaryDirectory(prefix=".resume-publish-", dir=directory) as temporary:
        build = Path(temporary)
        pdf = _compile_pdf(build, latex)
        checksum = _sha256(pdf.read_bytes())
        staged_latest = build / "latest.pdf"
        shutil.copyfile(pdf, staged_latest)
        previous_latest = build / "previous-latest.pdf"
        if latest.exists():
            shutil.copyfile(latest, previous_latest)
        staged_state = build / STATE_FILENAME
        staged_state.write_text(json.dumps({
            "version": 1,
            "current": filename,
            "fingerprint": fingerprint,
            "pdf_sha256": checksum,
        }, indent=2) + "\n", encoding="utf-8")

        archived = None
        installed = False
        latest_installed = False
        try:
            if previous is not None:
                archive.mkdir(exist_ok=True)
                archived = archive / _available_name(archive, previous.name)
                previous.replace(archived)
            pdf.replace(destination)
            installed = True
            staged_latest.replace(latest)
            latest_installed = True
            staged_state.replace(directory / STATE_FILENAME)
        except OSError:
            if latest_installed:
                if previous_latest.exists():
                    previous_latest.replace(latest)
                else:
                    latest.unlink()
            if installed:
                destination.unlink()
            if archived is not None and archived.exists():
                archived.replace(previous)
            raise
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        destination = publish_resume(Path(__file__).resolve().parent)
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f"Publication failed: {error}\n")
    if destination is None:
        print("No changes since the last publication; published files were left untouched.")
    else:
        print(f"Published {destination.name}; {LATEST_FILENAME} is the latest download.")


if __name__ == "__main__":
    main()