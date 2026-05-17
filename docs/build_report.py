"""Render docs/report.md -> submission/report.pdf using Chrome headless.

Dependencies:
  * Python 3.10+
  * `markdown` (pip install --user markdown)
  * Google Chrome installed at the standard Windows path
    (or set CHROME env var to the executable)

Usage:
  python docs/build_report.py
"""
from __future__ import annotations

import base64
import html
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parent.parent
MD_PATH = REPO_ROOT / "docs" / "report.md"
HTML_PATH = REPO_ROOT / "submission" / "report.html"
PDF_PATH = REPO_ROOT / "submission" / "report.pdf"


CSS = """
@page { size: A4; margin: 14mm 13mm 14mm 13mm; }

* { box-sizing: border-box; }

html { font-size: 10pt; }

body {
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a;
    line-height: 1.32;
    margin: 0;
}

h1, h2, h3, h4 {
    font-family: "Segoe UI Semibold", "Helvetica Neue", Arial, sans-serif;
    color: #0b3a78;
    page-break-after: avoid;
    margin-top: 0.7em;
    margin-bottom: 0.25em;
    line-height: 1.15;
}

h1 { font-size: 1.55em; border-bottom: 2px solid #0b3a78; padding-bottom: 0.15em; }
h2 { font-size: 1.2em; border-bottom: 1px solid #cfd9e8; padding-bottom: 0.1em; margin-top: 1em; }
h3 { font-size: 1.04em; color: #0a2d5a; }
h4 { font-size: 0.96em; color: #2a4a7a; }

p { margin: 0.28em 0 0.4em 0; }

ul, ol { margin: 0.2em 0 0.5em 0; padding-left: 1.25em; }
li { margin-bottom: 0.08em; }

a { color: #0b3a78; text-decoration: none; }
a:hover { text-decoration: underline; }

strong { color: #0a2d5a; }

code {
    font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
    font-size: 0.9em;
    background: #f1f3f7;
    padding: 0.02em 0.28em;
    border-radius: 3px;
}

pre {
    font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
    font-size: 7.4pt;
    line-height: 1.12;
    background: #f6f8fb;
    border: 1px solid #d8e0ec;
    border-radius: 4px;
    padding: 0.35em 0.55em;
    overflow: hidden;
    white-space: pre;
    page-break-inside: avoid;
    margin: 0.35em 0;
}

pre code { background: transparent; padding: 0; font-size: inherit; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.35em 0 0.6em 0;
    font-size: 0.9em;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #cfd9e8;
    padding: 0.22em 0.45em;
    text-align: left;
    vertical-align: top;
    line-height: 1.25;
}

th {
    background: #eaf0f9;
    color: #0a2d5a;
    font-weight: 600;
}

tr:nth-child(even) td { background: #fafbfd; }

blockquote {
    border-left: 3px solid #cfd9e8;
    color: #44546a;
    margin: 0.4em 0;
    padding: 0.05em 0.8em;
    font-style: italic;
}

hr {
    border: 0;
    border-top: 1px solid #d4dceb;
    margin: 0.9em 0;
}

/* Cover-page-ish styling for the title block */
h1:first-of-type {
    text-align: center;
    border: 0;
    margin-bottom: 0.05em;
    font-size: 2em;
}

h1:first-of-type + h3 {
    text-align: center;
    color: #44546a;
    margin-top: 0;
    border: 0;
}

/* Diagram images - centered, fit-width, keep on one page */
figure {
    margin: 0.6em 0 0.4em 0;
    text-align: center;
    page-break-inside: avoid;
}

figure img, p > img {
    max-width: 100%;
    height: auto;
    border: 1px solid #d8e0ec;
    border-radius: 4px;
}

figcaption {
    font-size: 0.85em;
    color: #44546a;
    margin-top: 0.25em;
    font-style: italic;
}

img.diagram {
    max-width: 100%;
    max-height: 16cm;
    object-fit: contain;
    display: block;
    margin: 0.4em auto;
    border: 1px solid #d8e0ec;
    border-radius: 4px;
}
"""


_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}


def inline_images(html_body: str, md_dir: Path) -> str:
    """Rewrite <img src="…"> tags to data: URLs so the rendered HTML is self-contained."""
    pattern = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)("[^>]*>)', re.IGNORECASE)

    def repl(m: re.Match[str]) -> str:
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        # resolve relative to the markdown file's directory
        candidate = (md_dir / src).resolve()
        if not candidate.exists():
            print(f"WARN: image not found, leaving src as-is: {src}", file=sys.stderr)
            return m.group(0)
        mime = _MIME.get(candidate.suffix.lower(), "application/octet-stream")
        b64 = base64.b64encode(candidate.read_bytes()).decode("ascii")
        return f'{prefix}data:{mime};base64,{b64}{suffix}'

    return pattern.sub(repl, html_body)


def main() -> int:
    if not MD_PATH.exists():
        print(f"ERROR: {MD_PATH} not found", file=sys.stderr)
        return 1

    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)

    md_text = MD_PATH.read_text(encoding="utf-8")

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "attr_list", "sane_lists"],
        output_format="html5",
    )
    html_body = inline_images(html_body, MD_PATH.parent)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>IUT Community - Design Report</title>
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>
"""
    HTML_PATH.write_text(html_doc, encoding="utf-8")
    print(f"wrote {HTML_PATH}")

    chrome = os.environ.get("CHROME") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not Path(chrome).exists():
        # try Edge
        chrome = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if not Path(chrome).exists():
            print("ERROR: Neither Chrome nor Edge found at the standard paths.", file=sys.stderr)
            print("Set the CHROME env var to the browser executable.", file=sys.stderr)
            return 2

    # file:// URL must be properly quoted on Windows
    url = "file:///" + urllib.parse.quote(str(HTML_PATH).replace("\\", "/"), safe="/:")

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        url,
    ]
    print("running:", " ".join(f'"{a}"' if " " in a else a for a in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("Chrome stderr:\n" + proc.stderr, file=sys.stderr)
        return proc.returncode

    if not PDF_PATH.exists():
        print("ERROR: Chrome returned 0 but the PDF was not produced.", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 3

    size_kb = PDF_PATH.stat().st_size / 1024
    print(f"wrote {PDF_PATH} ({size_kb:,.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
