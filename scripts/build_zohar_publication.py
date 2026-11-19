"""Build the Zohar Pages package from the existing local mind map."""

import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_mindmap import build_html

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN = ROOT / "output" / "mindmap_zohar_teszt.md"
SUMMARIES = ROOT / "input" / "zohar_summaries.json"
DESTINATION = ROOT / "docs"


def build_publication(markdown: str, summaries: dict[str, str]) -> str:
    """Create a Pages viewer using a separate same-origin summaries file."""
    document = build_html(markdown, summaries)
    document, count = re.subn(
        r'  <script type="application/json" id="node-summaries">[^\n]*</script>\n',
        "",
        document,
        count=1,
    )
    if count != 1:
        raise ValueError("A beagyazott osszefoglalok helye nem talalhato.")
    old = '      const summaries = JSON.parse(document.querySelector("#node-summaries").textContent);'
    new = """      let summaries;
      let requestId = 0;"""
    if old not in document:
        raise ValueError("Az osszefoglalok betoltesi pontja nem talalhato.")
    document = document.replace(old, new, 1)
    document = document.replace("      function open(node) {", "      async function open(node) {", 1)
    old = """        summary.textContent = Object.hasOwn(summaries, name)
          ? summaries[name] : "Ehhez a csomóponthoz nincs megadott összefoglaló.";
        panel.hidden = false;"""
    new = """        const currentRequest = ++requestId;
        panel.hidden = false;
        summary.textContent = "Összefoglaló betöltése…";
        try {
          if (!summaries) {
            summaries = fetch("./zohar_summaries.json").then(response => {
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return response.json();
            });
          }
          const data = await summaries;
          if (currentRequest !== requestId) return;
          summary.textContent = Object.hasOwn(data, name)
            ? data[name] : "Ehhez a csomóponthoz nincs megadott összefoglaló.";
        } catch (error) {
          summaries = undefined;
          console.error("Az összefoglalók betöltése sikertelen:", error);
          if (currentRequest === requestId) {
            summary.textContent = "Az összefoglalók nem tölthetők be. Ellenőrizd a JSON-fájlt és a hálózati kapcsolatot.";
          }
        }"""
    if old not in document:
        raise ValueError("Az osszefoglalo megjelenitesi pontja nem talalhato.")
    document = document.replace(old, new, 1)
    document = document.replace("        panel.hidden = true;\n", "        requestId++;\n        panel.hidden = true;\n", 1)
    return document


def main() -> None:
    markdown = MARKDOWN.read_text(encoding="utf-8")
    raw = SUMMARIES.read_text(encoding="utf-8-sig")
    summaries = json.loads(raw)
    document = build_publication(markdown, summaries)
    DESTINATION.mkdir(exist_ok=True)
    for path in (DESTINATION / "index.html", DESTINATION / "zohar_summaries.json"):
        if path.exists():
            raise FileExistsError(f"A kimenet mar letezik: {path}")
    (DESTINATION / "index.html").write_text(document, encoding="utf-8")
    (DESTINATION / "zohar_summaries.json").write_text(raw, encoding="utf-8")
    print(f"Elkeszult: {DESTINATION}")


if __name__ == "__main__":
    main()
