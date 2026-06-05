#!/usr/bin/env python3
"""Build printable HTML versions of the playbook Markdown files."""

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HTML_DIR = DOCS / "html"

FILES = [
    "leadership-dashboard-playbook.md",
    "technical-dashboard-playbook.md",
    "leadership-ai-chatbot-playbook.md",
    "technical-ai-chatbot-playbook.md",
    "dashboard-build-phased-playbook.md",
    "nvidia-dgx-spark-vs-jetson-agx-orin.md",
]


STYLE = """
:root {
  color-scheme: light;
  --ink: #1f2933;
  --muted: #52606d;
  --line: #d9e2ec;
  --brand: #d73f09;
  --soft: #fff5f0;
  --code: #f5f7fa;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--ink);
  background: #f7f8fa;
  line-height: 1.55;
}
main {
  max-width: 1080px;
  margin: 0 auto;
  padding: 40px 28px 80px;
  background: #fff;
  min-height: 100vh;
}
nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 0 28px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 28px;
}
nav a {
  color: var(--brand);
  text-decoration: none;
  border: 1px solid #f0b49e;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 14px;
}
h1 { font-size: 34px; line-height: 1.15; margin: 0 0 18px; color: #111827; }
h2 { font-size: 24px; margin-top: 34px; padding-top: 10px; border-top: 1px solid var(--line); }
h3 { font-size: 18px; margin-top: 26px; }
p, li { font-size: 16px; }
a { color: var(--brand); }
table { width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 15px; }
th, td { border: 1px solid var(--line); padding: 9px 11px; vertical-align: top; }
th { background: var(--soft); text-align: left; }
code { background: var(--code); padding: 2px 5px; border-radius: 4px; }
pre {
  overflow-x: auto;
  background: #111827;
  color: #f9fafb;
  padding: 16px;
  border-radius: 8px;
}
pre code { background: transparent; padding: 0; color: inherit; }
.mermaid {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
  margin: 18px 0;
}
.meta {
  color: var(--muted);
  font-size: 14px;
  margin-bottom: 18px;
}
@media print {
  body { background: #fff; }
  main { max-width: none; padding: 0; }
  nav { display: none; }
  h2 { break-after: avoid; }
  pre, table { break-inside: avoid; }
}
"""


def inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def parse_table(lines: list[str], start: int) -> tuple[str, int] | None:
    if start + 1 >= len(lines):
        return None
    if not lines[start].lstrip().startswith("|"):
        return None
    if not re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[start + 1]):
        return None

    rows = []
    index = start
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        rows.append(cells)
        index += 1

    header = rows[0]
    body = rows[2:]
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{inline(cell)}</th>" for cell in header)
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>")
        out.extend(f"<td>{inline(cell)}</td>" for cell in row)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out), index


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    in_ul = False
    in_ol = False
    para: list[str] = []

    def close_para() -> None:
        nonlocal para
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                if code_lang == "mermaid":
                    out.append(f'<div class="mermaid">\n{html.escape(chr(10).join(code_lines))}\n</div>')
                else:
                    out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                in_code = False
                code_lang = ""
                code_lines = []
            else:
                close_para()
                close_lists()
                in_code = True
                code_lang = stripped[3:].strip()
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        table = parse_table(lines, i)
        if table:
            close_para()
            close_lists()
            table_html, i = table
            out.append(table_html)
            continue

        if not stripped:
            close_para()
            close_lists()
            i += 1
            continue

        match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if match:
            close_para()
            close_lists()
            level = len(match.group(1))
            out.append(f"<h{level}>{inline(match.group(2))}</h{level}>")
            i += 1
            continue

        if stripped.startswith("- "):
            close_para()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
            i += 1
            continue

        ordered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered:
            close_para()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline(ordered.group(1))}</li>")
            i += 1
            continue

        close_lists()
        para.append(stripped)
        i += 1

    close_para()
    close_lists()
    return "\n".join(out)


def page(title: str, body: str) -> str:
    links = "\n".join(
        f'<a href="{Path(name).with_suffix(".html").name}">{Path(name).stem.replace("-", " ").title()}</a>'
        for name in FILES
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{STYLE}</style>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
  </script>
</head>
<body>
  <main>
    <nav>{links}</nav>
    <div class="meta">Living HTML version generated from Markdown source. Use Chrome Print to export PDF.</div>
    {body}
  </main>
</body>
</html>
"""


def main() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        source = DOCS / filename
        markdown = source.read_text(encoding="utf-8")
        title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), source.stem)
        rendered = markdown_to_html(markdown)
        target = HTML_DIR / Path(filename).with_suffix(".html").name
        target.write_text(page(title, rendered), encoding="utf-8")

    index_links = "\n".join(
        f'<li><a href="{Path(name).with_suffix(".html").name}">{Path(name).stem.replace("-", " ").title()}</a></li>'
        for name in FILES
    )
    (HTML_DIR / "index.html").write_text(
        page("OSU Presentation Support Platform Playbooks", f"<h1>OSU Presentation Support Platform Playbooks</h1><ul>{index_links}</ul>"),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
