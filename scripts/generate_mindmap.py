"""Generate a deterministic Markdown mind map and a Markmap HTML viewer."""

import argparse
import html
import json
import re
import sys
from pathlib import Path

MARKMAP_URL = "https://cdn.jsdelivr.net/npm/markmap-autoloader@0.18.12/dist/index.js"
VIEWER_TEMPLATE = Path(__file__).with_name("mindmap_viewer.html")


def _literal(text: str) -> str:
    """Keep source text literal in both Markdown and Markmap's HTML renderer."""
    text = html.escape(text, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#!+|>~-])", r"\\\1", text)


def build_markdown(source: str) -> str:
    """Turn headings, indented lists and keyword: detail lines into branches."""
    if not source.strip():
        raise ValueError("A bemeneti szoveg ures.")
    lines = ["# Gondolattérkép", ""]
    headings: list[int] = []
    indent_stack: list[int] = []
    for raw in source.splitlines():
        if not raw.strip():
            indent_stack.clear()
            continue
        expanded = raw.expandtabs(4)
        stripped = expanded.strip()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            while headings and headings[-1] >= level:
                headings.pop()
            lines.append("  " * len(headings) + "- " + _literal(heading.group(2).strip()))
            headings.append(level)
            indent_stack.clear()
            continue
        indent = len(expanded) - len(expanded.lstrip())
        while indent_stack and indent_stack[-1] > indent:
            indent_stack.pop()
        if not indent_stack or indent_stack[-1] < indent:
            indent_stack.append(indent)
        depth = len(headings) + len(indent_stack) - 1
        content = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", stripped)
        keyword, separator, detail = content.partition(":")
        if separator and keyword.strip() and detail.strip():
            lines.append("  " * depth + "- " + _literal(keyword.strip()))
            lines.append("  " * (depth + 1) + "- " + _literal(detail.strip()))
        else:
            lines.append("  " * depth + "- " + _literal(content))
    return "\n".join(lines) + "\n"


def build_html(markdown: str, summaries: dict[str, str] | None = None) -> str:
    """Embed inert Markdown and optional node summaries in the viewer."""
    data = summaries if summaries is not None else {}
    if not isinstance(data, dict) or any(
        not isinstance(key, str) or not key.strip()
        or not isinstance(value, str) or not value.strip()
        for key, value in data.items()
    ):
        raise ValueError("Az osszefoglalok nem ures szoveges kulcsok es ertekek legyenek.")
    encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    template = VIEWER_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "MARKDOWN": html.escape(markdown),
        "SUMMARIES": encoded,
        "MARKMAP_URL": MARKMAP_URL,
    }
    return re.sub(
        r"\{\{(MARKDOWN|SUMMARIES|MARKMAP_URL)\}\}",
        lambda match: replacements[match.group(1)],
        template,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Gondolatterkep generalasa szovegbol.")
    parser.add_argument("--input", type=Path, default=Path("input/source.txt"))
    parser.add_argument("--markdown", type=Path, default=Path("output/mindmap.md"))
    parser.add_argument("--html", type=Path, default=Path("output/mindmap.html"))
    parser.add_argument("--from-markdown", action="store_true",
                        help="A bemenet mar elkeszult Markdown-terkep.")
    parser.add_argument("--summaries", type=Path,
                        help="JSON objektum: csomopont szovege -> osszefoglalo.")
    parser.add_argument("--force", action="store_true", help="Meglevo kimenetek felulirasa.")
    args = parser.parse_args()
    try:
        source, markdown_path, html_path = (
            args.input.resolve(), args.markdown.resolve(), args.html.resolve()
        )
        reuse_source = args.from_markdown and source == markdown_path
        if html_path in {source, markdown_path} or (source == markdown_path and not reuse_source):
            raise ValueError("A bemenet es a ket kimenet kulonbozo fajl legyen.")
        if args.summaries and args.summaries.resolve() in {markdown_path, html_path}:
            raise ValueError("Az osszefoglalok fajlja nem lehet kimenet.")
        if not args.force:
            for output in ([args.html] if reuse_source else [args.markdown, args.html]):
                if output.exists():
                    raise FileExistsError(f"A kimenet mar letezik: {output}")
        text = args.input.read_text(encoding="utf-8-sig")
        markdown = text if args.from_markdown else build_markdown(text)
        if not markdown.strip():
            raise ValueError("A bemeneti szoveg ures.")
        summaries = (json.loads(args.summaries.read_text(encoding="utf-8-sig"))
                     if args.summaries else None)
        document = build_html(markdown, summaries)
        for output in (args.markdown, args.html):
            output.parent.mkdir(parents=True, exist_ok=True)
        if not reuse_source:
            args.markdown.write_text(markdown, encoding="utf-8")
        args.html.write_text(document, encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Hiba: {exc}", file=sys.stderr)
        return 1
    print(f"Elkeszult: {args.markdown}, {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
