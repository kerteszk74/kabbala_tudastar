"""Export an explicitly authorized corpus and its map to the Pages directory."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
STOPWORDS = frozenset(
    "the and for that with this from are was were which his her not but they "
    "their into when all then she you him its also have one will upon them "
    "az és egy hogy mint aki ami ezt arra van nem mert vagy csak már meg "
    "minden amely azt ahol saját más ezt".split()
)


def keywords(text: str) -> list[str]:
    normalized = "".join(
        char for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )
    words = re.findall(r"[^\W\d_]{4,}", normalized)
    counts = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _ in counts.most_common(12)]


def chunks(text: str, size: int = 550, overlap: int = 100) -> list[str]:
    words = text.split()
    result = []
    start = 0
    while start < len(words):
        result.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
        start += size - overlap
    return result


def document_blocks(path: Path, volume: int) -> list[dict[str, Any]]:
    document = Document(path)
    chapter = "Cím nélküli bevezető"
    paragraphs: list[str] = []
    result: list[dict[str, Any]] = []

    def flush() -> None:
        for text in chunks(" ".join(paragraphs)):
            identity = f"{path.name}\0{len(result)}\0{chapter}\0{text}"
            result.append({
                "id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
                "kotet": volume,
                "fajl": path.name,
                "fejezet": chapter,
                "szoveg": text,
                "kulcsszavak": keywords(text),
            })
        paragraphs.clear()

    for element in document.element.body.iter(qn("w:p")):
        paragraph = Paragraph(element, document)
        text = paragraph.text.strip()
        if not text:
            continue
        style = paragraph.style
        name = style.name.lower() if style is not None else ""
        if name.startswith(("heading ", "címsor ", "myheading", "chapter")):
            flush()
            chapter = text
        else:
            paragraphs.append(text)
    flush()
    if not result:
        raise ValueError(f"Nincs indexelhető szöveg: {path.name}")
    return result


def map_nodes(root: object) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: object, volume: int, depth: int) -> None:
        if not isinstance(node, dict):
            raise ValueError("A gondolattérkép csomópontja nem objektum.")
        title, summary, children = node.get("title"), node.get("summary"), node.get("children")
        if not isinstance(title, str) or not title.strip() or not isinstance(summary, dict):
            raise ValueError("Hibás gondolattérkép-cím vagy magyarázat.")
        if not isinstance(children, list) or any(
            not isinstance(summary.get(key), str) or not summary[key].strip()
            for key in ("intro", "inner_meaning", "connection")
        ):
            raise ValueError(f"Hiányos gondolattérkép-csomópont: {title}")
        nodes.append({
            "id": str(len(nodes)), "kotet": volume, "cim": title,
            "magyarazat": {key: summary[key] for key in ("intro", "inner_meaning", "connection")},
        })
        for index, child in enumerate(children):
            visit(child, index + 1 if depth == 0 else volume, depth + 1)

    if not isinstance(root, dict) or not isinstance(root.get("children"), list) or len(root["children"]) != 4:
        raise ValueError("A gondolattérképnek pontosan négy kötetet kell tartalmaznia.")
    visit(root, 0, 0)
    return nodes


def main() -> int:
    try:
        sources = sorted(
            (p for p in (ROOT / "sources").glob("*.docx") if not p.name.startswith("~$")),
            key=lambda p: p.name.casefold(),
        )
        if len(sources) != 4:
            raise ValueError(f"Pontosan négy DOCX szükséges, megtalálva: {len(sources)}.")
        raw = (ROOT / "zohar_summaries.json").read_text(encoding="utf-8-sig")
        nodes = map_nodes(json.loads(raw))
        blocks = [block for index, path in enumerate(sources, 1)
                  for block in document_blocks(path, index)]
        payload = json.dumps({"verzio": 1, "blokkok": blocks, "csomopontok": nodes},
                             ensure_ascii=False, separators=(",", ":"))
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        docs = ROOT / "docs"
        docs.mkdir(exist_ok=True)
        (ROOT / "zohar_web_rag.json").write_text(payload, encoding="utf-8")
        (docs / "zohar_web_rag.json").write_text(payload, encoding="utf-8")
        (docs / "zohar_summaries.json").write_text(raw, encoding="utf-8")
        (docs / "index.html").write_text(html, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Exportálási hiba: {exc}", file=sys.stderr)
        return 1
    print(f"Exportálva: {len(blocks)} szövegblokk, {len(nodes)} térképcsomópont; cél: {docs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
