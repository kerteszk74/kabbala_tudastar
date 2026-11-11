import json
from pathlib import Path

from scripts.build_zohar_publication import build_publication


def test_publication_uses_relative_json_without_embedded_data() -> None:
    html = build_publication("# Teszt\n- Fogalom\n", {"Fogalom": "Egyedi adat."})
    assert 'fetch("./zohar_summaries.json")' in html
    assert "Egyedi adat." not in html
    assert "node-summaries" not in html
    assert "Összefoglalók nem tölthetők be" in html or "összefoglalók nem tölthetők be" in html


def test_publication_covers_every_zohar_node() -> None:
    root = Path(__file__).resolve().parents[1]
    markdown = (root / "output" / "mindmap_zohar_teszt.md").read_text(encoding="utf-8")
    summaries = json.loads((root / "input" / "zohar_summaries.json").read_text(encoding="utf-8"))
    nodes = {
        line.lstrip("#- ").strip()
        for line in markdown.splitlines()
        if line.lstrip().startswith(("# ", "## ", "- "))
    }
    assert nodes == set(summaries)
    assert len(nodes) == 45
    assert "Zohár - Bevezető fejezet" in build_publication(markdown, summaries)
