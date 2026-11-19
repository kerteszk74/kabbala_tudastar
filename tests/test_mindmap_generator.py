import subprocess
import sys
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

from scripts.generate_mindmap import build_html, build_markdown


def test_hierarchy_and_keywords() -> None:
    source = "# Energia\n- Napenergia\n  - Panel\n## Tarolas\nAkkumulator: Lithium\n# Masik\n- Szél"
    markdown = build_markdown(source)
    assert markdown == (
        "# Gondolattérkép\n\n"
        "- Energia\n"
        "  - Napenergia\n"
        "    - Panel\n"
        "  - Tarolas\n"
        "    - Akkumulator\n"
        "      - Lithium\n"
        "- Masik\n"
        "  - Szél\n"
    )


def test_untrusted_text_stays_inert() -> None:
    text = "</pre><script>alert('x')</script>\n[link](javascript:alert(1))"
    document = build_html(build_markdown(text))

    class Tags(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.scripts = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "script":
                self.scripts.append(dict(attrs))

    parser = Tags()
    parser.feed(document)
    assert len(parser.scripts) == 3
    assert parser.scripts[0]["type"] == "application/json"
    assert parser.scripts[-1]["src"].startswith("https://cdn.jsdelivr.net/")
    assert "&amp;lt;/pre&amp;gt;" in document
    assert r"\[link\]" in document


def test_summaries_are_embedded_as_inert_json() -> None:
    document = build_html("# Téma", {"Téma": "</script><script>alert(1)</script>"})
    assert r"\u003c/script>" in document
    assert 'id="node-summaries"' in document
    assert "summary.textContent" in document
    assert "{{SUMMARIES}}" not in document
    assert "{{SUMMARIES}}" in build_html("# {{SUMMARIES}}", {"x": "y"})


@pytest.mark.parametrize("data", [[], {"x": 1}, {"": "x"}, {"x": ""}])
def test_invalid_summaries_are_rejected(data: object) -> None:
    with pytest.raises(ValueError, match="osszefoglalok"):
        build_html("# Téma", data)  # type: ignore[arg-type]


def test_existing_markdown_and_summaries_cli(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Téma\n- Részlet\n", encoding="utf-8")
    summaries = tmp_path / "summaries.json"
    summaries.write_text(json.dumps({"Téma": "Első mondat. Második mondat."}), encoding="utf-8")
    output = tmp_path / "output.html"
    script = Path(__file__).resolve().parents[1] / "scripts" / "generate_mindmap.py"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(source), "--from-markdown",
         "--markdown", str(source), "--html", str(output), "--summaries", str(summaries)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert source.read_text(encoding="utf-8") == "# Téma\n- Részlet\n"
    assert "Első mondat. Második mondat." in output.read_text(encoding="utf-8")


def test_empty_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="ures"):
        build_markdown(" \n ")


def test_cli_outputs_and_prevents_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("# Téma\n- Részlet", encoding="utf-8")
    markdown, html = tmp_path / "map.md", tmp_path / "map.html"
    script = Path(__file__).resolve().parents[1] / "scripts" / "generate_mindmap.py"
    command = [sys.executable, str(script), "--input", str(source),
               "--markdown", str(markdown), "--html", str(html)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "Téma" in markdown.read_text(encoding="utf-8")
    assert "markmap-autoloader@0.18.12" in html.read_text(encoding="utf-8")
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode == 1
    assert "mar letezik" in second.stderr
    forced = subprocess.run([*command, "--force"], capture_output=True, text=True, check=False)
    assert forced.returncode == 0, forced.stderr
