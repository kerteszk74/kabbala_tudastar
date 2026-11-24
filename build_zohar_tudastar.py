"""Build the hybrid mind map's indexes from the complete local Zohar book.

Run: python build_zohar_tudastar.py
No network access, model calls, or third-party Python packages are required.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
BOOK = ROOT / "forrasok" / "zohar" / "zohar_teljes_konyv.md"
EXPECTED = (13, 2165, 23555)
LABEL = "Zohár mindenkinek - Rashbi | "
SYNONYMS = [
    ["reflected light", "visszaverődő fény", "visszavert fény", "ór hozer", "or hozer"],
    ["purpose of creation", "teremtés célja", "a teremtés célja"],
    ["light", "lights", "fény", "ór"],
    ["vessel", "vessels", "edény", "kli", "keli", "kelim"],
    ["creator", "teremtő"],
    ["desire", "desires", "will", "vágy", "akarat"],
    ["screen", "screens", "képernyő", "ellenző", "maszah", "masach", "maszach"],
    ["restriction", "cimcum", "tzimtzum", "megszorítás"],
    ["bestowal", "bestow", "adakozás", "adás", "adakozó"],
    ["receive", "receiving", "reception", "befogadás", "megszerzés"],
    ["soul", "souls", "lélek", "lelkek"],
    ["creation", "teremtés"],
    ["wisdom", "bölcsesség", "hohma", "hochma", "chochma"],
    ["bina", "biná", "binah"],
    ["malchut", "malhut", "malchuth"],
    ["hesed", "heszed", "chesed"],
    ["gevura", "gvura", "gevurah"],
    ["tifferet", "tiferet", "tifereth"],
    ["netzah", "necah", "netzach"],
    ["yesod", "jeszod", "jesod"],
    ["hassadim", "hasadim", "haszadim", "chasadim"],
    ["klipa", "klipot", "klipah", "klipót", "klipótok", "shells"],
    ["sefirot", "szefira", "szefirák", "szefirot", "sefira", "sefiroth"],
    ["partzuf", "partzufim", "parcuf", "parcufim"],
    ["atzilut", "acilut", "atziluth"],
    ["beria", "beriah"],
    ["yetzira", "jecira"],
    ["assiya", "aszija", "assiyah"],
    ["rose", "rózsa"],
    ["assembly", "gyülekezet"],
    ["israel", "izrael"],
    ["love", "szeretet"],
    ["unity", "egység", "egyesülés"],
    ["correction", "korrekció", "tikkun", "tikun"],
    ["intention", "szándék", "kavana", "kavaná"],
    ["upper", "felső"],
    ["lower", "alsó"],
    ["prayer", "ima", "imádság"],
    ["torah", "tóra"],
]
PREFIXES = {
    "feny": "light", "edeny": "vessel", "teremto": "creator",
    "akarat": "desire", "kepernyo": "screen", "adakoz": "bestowal",
    "megszerz": "receive", "befogad": "receive", "szandek": "intention",
    "szeretet": "love", "lelk": "soul",
}
STOPWORDS = set(
    "a az es egy hogy mi mit milyen hogyan van volt vagy is de nem szerepe jelent "
    "jelentenek kapcsolata tanitas belso szellemi the and of to in is are what how "
    "does for with from on into as it this that be by was were his her their them "
    "they he she at not all but an its which has have had also there then when "
    "who will through can one two said says thus these those more than or if "
    "you your i we our us so only because each every no do".split()
)


def normalize(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if not unicodedata.combining(char)
    )


def alias_rules() -> list[tuple[re.Pattern, str]]:
    aliases = {
        normalize(alias): normalize(group[0])
        for group in SYNONYMS for alias in group if normalize(alias) != "vagy"
    }
    return [
        (re.compile(r"(?<!\w)" + re.escape(alias) + r"(?!\w)"), canonical)
        for alias, canonical in sorted(aliases.items(), key=lambda item: -len(item[0]))
        if alias != canonical
    ]


RULES = alias_rules()


def tokens(text: str) -> list[str]:
    # Keep accented "vagy" (desire) distinct from the Hungarian conjunction.
    text = re.sub(r"vágy[^\W\d_]*", " desire ", text.lower())
    text = normalize(text)
    for pattern, canonical in RULES:
        text = pattern.sub(canonical, text)
    result = []
    for word in re.findall(r"[^\W_]+", text):
        if word in STOPWORDS or len(word) < 2:
            continue
        result.append(next(
            (canonical for prefix, canonical in PREFIXES.items() if word.startswith(prefix)),
            word,
        ))
    return result


def plain_text(markdown: str) -> str:
    text = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", markdown)
    text = re.sub(r"(?m)^#{1,6}\s+", "", text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.replace("**", "").replace("*", "").strip()


def clean_summary(text: str) -> str:
    text = re.sub(r"\s*(?:#{1,6}\s+)?(?:\*\*)?Források:(?:\*\*)?[\s\S]*$", "", text)
    text = re.sub(r"\s*\[(?:[a-fA-F0-9]{64}|T\d+|F[0-9a-f]+)\]", "", text)
    text = re.sub(r"\s*\[\d+\](?:\s*[–-]\s*\[\d+\])?", "", text)
    text = re.sub(r"(?:,\s*)+(?=[,.;:!?]|$)", "", text)
    return re.sub(r"[ \t]+([,.;:!?])", r"\1", text).strip()


def parse_book(markdown: str) -> tuple[list[dict], list[dict], dict[str, dict]]:
    anchors = list(re.finditer(r'(?m)^<a id="source-([A-Za-z0-9]+)"></a>\s*$', markdown))
    if not anchors:
        raise ValueError("A könyvben nincsenek forrásazonosítók.")
    chapters, points, bodies = [], [], {}
    seen = set()
    for index, anchor in enumerate(anchors):
        uid = anchor[1]
        if uid in seen:
            raise ValueError(f"Ismételt fejezetazonosító: {uid}")
        seen.add(uid)
        end = anchors[index + 1].start() if index + 1 < len(anchors) else len(markdown)
        block = markdown[anchor.end():end]
        title = re.search(r"(?m)^### (.+)$", block)
        path = re.search(r"(?m)^Path: (.+)$", block)
        language = re.search(r"(?m)^Language: (en|he)\s*$", block)
        source = re.search(r"(?m)^Source: (\S+)", block)
        content = re.search(r"(?m)^Official download: \S+[ \t]*\r?\n", block)
        if not all((title, path, language, source, content)):
            raise ValueError(f"Hiányos fejezetfejléc: {uid}")
        assert title and path and language and source and content
        volume = re.search(r"(?:^| / )Vol\. (\d+)(?: / |$)", path[1])
        url = urlparse(source[1])
        if (
            volume is None or url.scheme != "https"
            or url.netloc != "kabbalahmedia.info"
            or url.path != f"/en/sources/{uid}"
            or parse_qs(url.query).get("source_language") != [language[1]]
        ):
            raise ValueError(f"Hibás kötet vagy forrás-URL: {uid}")
        body = re.split(r"(?m)^## Vol\. \d+\s*$|^---\s*$", block[content.end():], maxsplit=1)[0].strip()
        markers = list(re.finditer(
            r"(?m)^[\u200e\u200f\u202a-\u202e\u2066-\u2069]*(\d+)[).][ \t\u200e\u200f]*",
            body,
        ))
        chapter_points = []
        occurrences: Counter[int] = Counter()
        for position, marker in enumerate(markers):
            number = int(marker[1])
            occurrences[number] += 1
            stop = markers[position + 1].start() if position + 1 < len(markers) else len(body)
            text = plain_text(body[marker.end():stop])
            if not text:
                raise ValueError(f"Üres pontszöveg: {uid}, {number}")
            point = {
                "id": f"{uid}:{number}:{occurrences[number]}",
                "chapter_id": uid, "number": number,
                "occurrence": occurrences[number], "text": text,
            }
            chapter_points.append(point)
        numbers = [point["number"] for point in chapter_points]
        chapter = {
            "id": uid, "title": title[1].strip(), "volume": int(volume[1]),
            "path": path[1].split(" / "), "language": language[1],
            "source_url": source[1], "point_count": len(chapter_points),
            "point_range": [min(numbers), max(numbers)] if numbers else None,
            "preview_file": f"chapters/{uid}.json",
        }
        preamble = plain_text(body[:markers[0].start()] if markers else body)
        chapters.append(chapter)
        points.extend(chapter_points)
        bodies[uid] = {"id": uid, "preamble": preamble, "points": chapter_points}
    return chapters, points, bodies


def base36(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = alphabet[remainder] + result
    return result or "0"


def encode_postings(positions: list[int]) -> str:
    previous = 0
    deltas = []
    for position in positions:
        deltas.append(base36(position - previous))
        previous = position
    return ".".join(deltas)


def search_documents(chapters: list[dict], points: list[dict], bodies: dict[str, dict]):
    chapter_numbers = {chapter["id"]: index for index, chapter in enumerate(chapters)}
    documents = [
        [chapter_numbers[point["chapter_id"]], point["number"], point["occurrence"], point["id"]]
        for point in points
    ]
    texts = [point["text"] for point in points]
    for index, chapter in enumerate(chapters):
        if chapter["point_count"] == 0:
            documents.append([index, None, 1, chapter["id"] + ":unnumbered"])
            texts.append(bodies[chapter["id"]]["preamble"])
    postings: dict[str, list[int]] = defaultdict(list)
    lengths, keywords = [], []
    for position, (document, text) in enumerate(zip(documents, texts)):
        words = tokens(chapters[document[0]]["title"] + " " + text)
        lengths.append(len(words))
        counts = Counter(word for word in words if not word.isdigit())
        keywords.append(sorted(counts, key=lambda word: (-counts[word], word))[:8])
        for word in set(words):
            postings[word].append(position)
    return documents, postings, lengths, keywords


def node_references(tree: dict, documents: list, postings: dict, lengths: list) -> dict:
    references = {}
    count = len(documents)
    average_length = sum(lengths) / count

    def visit(node: dict) -> None:
        identifier = str(len(references))
        weights = Counter(word for word in tokens(node["title"]) if word not in ("zohar", "kotet"))
        for word in weights:
            weights[word] *= 4
        for value in node["summary"].values():
            for word in set(tokens(value)):
                weights[word] += 0.15
        scores: dict[int, float] = defaultdict(float)
        for word, weight in weights.items():
            matches = postings.get(word, [])
            inverse = math.log(1 + count / (1 + len(matches)))
            for position in matches:
                scores[position] += weight * inverse / (0.5 + 0.5 * lengths[position] / average_length)
        selected, seen_chapters = [], set()
        for position in sorted(scores, key=lambda item: (-scores[item], item)):
            chapter = documents[position][0]
            if chapter in seen_chapters or documents[position][1] is None:
                continue
            selected.append(documents[position][3])
            seen_chapters.add(chapter)
            if len(selected) == 3:
                break
        references[identifier] = selected
        for child in node["children"]:
            visit(child)

    visit(tree)
    return references


def write_json(path: Path, data: object, indent: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(
            data, ensure_ascii=False, indent=indent, allow_nan=False,
            separators=(",", ":") if indent is None else None,
        ),
        encoding="utf-8", newline="\n",
    )
    temporary.replace(path)


def build() -> dict:
    raw = BOOK.read_bytes()
    chapters, points, bodies = parse_book(raw.decode("utf-8"))
    volumes = sorted({chapter["volume"] for chapter in chapters})
    actual = (len(volumes), len(chapters), len(points))
    if actual != EXPECTED or volumes != list(range(1, 14)):
        raise ValueError(f"Hiányos könyvindex: {actual}; elvárt: {EXPECTED}")
    stats = {
        "volumes": len(volumes), "chapters": len(chapters), "points": len(points),
        "unnumbered_chapters": sum(chapter["point_count"] == 0 for chapter in chapters),
        "book_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_line_point_markers": len(re.findall(r"(?m)^\d+[).]", raw.decode("utf-8"))),
    }
    stats["direction_marker_points"] = stats["points"] - stats["raw_line_point_markers"]
    index = {
        "version": 3, "content_mode": "metadata_only", "stats": stats,
        "volumes": [{"id": number, "title": f"{number}. kötet"} for number in volumes],
        "chapters": chapters,
    }
    documents, postings, lengths, keywords = search_documents(chapters, points, bodies)
    search_index = {
        "version": 3, "content_mode": "metadata_only", "stats": stats,
        "documents": documents, "lengths": lengths, "keywords": keywords,
        "synonyms": SYNONYMS, "prefixes": PREFIXES, "stopwords": sorted(STOPWORDS),
        "postings": {word: encode_postings(values) for word, values in sorted(postings.items())},
    }
    tree = json.loads((ROOT / "zohar_summaries.json").read_text(encoding="utf-8-sig"))

    def clean_node(node: dict) -> None:
        for key, value in node["summary"].items():
            node["summary"][key] = clean_summary(value)
        for child in node["children"]:
            clean_node(child)

    clean_node(tree)
    references = node_references(tree, documents, postings, lengths)
    keyword_by_id = {document[3]: words for document, words in zip(documents, keywords)}
    referenced_ids = sorted({uid for items in references.values() for uid in items})
    for destination in (ROOT / "data", ROOT / "docs" / "data"):
        write_json(destination / "zohar_chapters_index.json", index)
        write_json(destination / "zohar_search_index.json", search_index)
        write_json(destination / "zohar_node_references.json", {
            "version": 3, "content_mode": "metadata_only", "stats": stats,
            "references": references,
            "keywords": {uid: keyword_by_id[uid] for uid in referenced_ids},
        })
    for chapter in chapters:
        local_preview = ROOT / "data" / chapter["preview_file"]
        write_json(local_preview, bodies[chapter["id"]])
        obsolete_preview = ROOT / "docs" / "data" / chapter["preview_file"]
        if obsolete_preview.exists():
            if obsolete_preview.read_bytes() != local_preview.read_bytes():
                raise ValueError(f"Eltérő helyi előnézet; nem töröljük: {obsolete_preview}")
            obsolete_preview.unlink()
    write_json(ROOT / "data" / "zohar_points_index.json", {
        "version": 2, "stats": stats, "chapters": chapters, "points": points,
        "unnumbered": [
            {"id": chapter["id"] + ":unnumbered", "chapter_id": chapter["id"],
             "text": bodies[chapter["id"]]["preamble"]}
            for chapter in chapters if chapter["point_count"] == 0
        ],
    })
    for path in (ROOT / "zohar_summaries.json", ROOT / "docs" / "zohar_summaries.json"):
        write_json(path, tree, indent=2)
    assets = ROOT / "docs" / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets" / "zohar_search.js", assets / "zohar_search.js")
    shutil.copyfile(ROOT / "assets" / "zohar_library.js", assets / "zohar_library.js")
    shutil.copyfile(ROOT / "index.html", ROOT / "docs" / "index.html")
    docs = ROOT / "docs"
    (docs / ".nojekyll").touch()
    (ROOT / ".nojekyll").touch()
    web_paths = [
        docs / "index.html", docs / "zohar_summaries.json",
        assets / "zohar_search.js", assets / "zohar_library.js",
        *(docs / "data" / name for name in (
            "zohar_chapters_index.json", "zohar_search_index.json",
            "zohar_node_references.json",
        )),
    ]
    manifest = []
    for path in sorted(web_paths):
        content = path.read_bytes()
        if len(content) >= 15_000_000:
            raise ValueError(f"Túl nagy webes adatfájl (15 MB): {path}")
        manifest.append({
            "path": path.relative_to(docs).as_posix(), "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    write_json(docs / "web_assets_manifest.json", {
        "version": 1, "content_mode": "metadata_only", "book_sha256": stats["book_sha256"],
        "total_bytes": sum(item["bytes"] for item in manifest),
        "files": manifest,
    })
    shutil.copyfile(docs / "web_assets_manifest.json", ROOT / "web_assets_manifest.json")
    print(json.dumps(stats, ensure_ascii=False))
    print(f"Search index: {(ROOT / 'data' / 'zohar_search_index.json').stat().st_size:,} bytes")
    return stats


if __name__ == "__main__":
    build()
