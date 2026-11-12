import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from docx import Document
from google import genai
from google.genai import types

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-4-carbon")

SYSTEM_PROMPT = """
Te a Kabbala és a Zohár autentikus, mégis rendkívül közérthető tanítója vagy.
A feladatod, hogy a megadott Zohár forrásszövegből egy hierarchikus gondolattérképet (tudásfát) építs fel olyan olvasóknak, AKIK MOST ISMERKEDNEK A KABBALÁVAL.

Szabályok minden egyes csomóponthoz:
1. Kerüld a megmagyarázatlan héber/arámi szakkifejezéseket! Ha szerepel egy alapfogalom (pl. Cimcum, Keli, Ór, Szefirák, Klipot), azonnal fordítsd le hétköznapi nyelvre és szemléletes hasonlatra.
2. Minden csomópont összefoglalója pontosan 3 mezőből álljon:
   - "intro": Miről szól ez a téma? (Világos, barátságos bevezető és hétköznapi analógia.)
   - "inner_meaning": Mi a belső, szellemi üzenete? (A vágyak működése, az adás és befogadás szándéka közérthetően.)
   - "connection": Hogyan kapcsolódik a térkép többi részéhez? (Miért következik ez az előző ágból, és milyen felismeréshez vezet tovább.)
3. Készíts 4-6 főágat, és mindegyikhez 2-4 alágat (összesen kb. 20-30 gazdagon kifejtett csomópontot), hogy a térkép átlátható, mégis tartalmas legyen.

Kizárólag érvényes JSON struktúrát adj vissza az alábbi sémában:
{
  "title": "Főcím",
  "summary": {
    "intro": "...",
    "inner_meaning": "...",
    "connection": "..."
  },
  "children": [
    {
      "title": "Alág címe",
      "summary": {
        "intro": "...",
        "inner_meaning": "...",
        "connection": "..."
      },
      "children": []
    }
  ]
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zohár Gondolattérkép – Kezdőbarát Tudástár</title>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.17.0"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.17.0"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    header {
      background: #1e293b;
      padding: 12px 20px;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }
    header h1 { font-size: 1.1rem; color: #38bdf8; font-weight: 600; }
    header .hint { font-size: 0.85rem; color: #94a3b8; }
    #container { position: relative; flex: 1; display: flex; overflow: hidden; }
    #mindmap { width: 100%; height: 100%; background: #0f172a; }
    .markmap-node text, .markmap-node div {
      fill: #f1f5f9 !important;
      color: #f1f5f9 !important;
      cursor: pointer;
    }
    .markmap-node div:hover { color: #38bdf8 !important; text-decoration: underline; }
    #detail-panel {
      position: fixed;
      top: 0;
      right: -460px;
      width: 440px;
      max-width: 92vw;
      height: 100vh;
      background: #1e293b;
      border-left: 1px solid #38bdf8;
      box-shadow: -8px 0 24px rgba(0, 0, 0, 0.5);
      transition: right 0.3s ease;
      z-index: 100;
      display: flex;
      flex-direction: column;
    }
    #detail-panel.open { right: 0; }
    .panel-header {
      padding: 18px 20px;
      background: #0f172a;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
    }
    .breadcrumb { font-size: 0.78rem; color: #38bdf8; margin-bottom: 6px; line-height: 1.4; }
    #panel-title { font-size: 1.25rem; color: #ffffff; line-height: 1.3; }
    #close-btn {
      background: transparent;
      border: 1px solid #475569;
      color: #cbd5e1;
      font-size: 1.2rem;
      width: 32px;
      height: 32px;
      border-radius: 6px;
      cursor: pointer;
      flex-shrink: 0;
    }
    #close-btn:hover { background: #334155; color: #fff; }
    .panel-body {
      padding: 20px;
      overflow-y: auto;
      flex: 1;
      line-height: 1.65;
      font-size: 0.96rem;
    }
    .section-card {
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 14px;
    }
    .section-card h3 {
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #38bdf8;
      margin-bottom: 8px;
    }
    .section-card p { color: #e2e8f0; white-space: pre-line; }
  </style>
</head>
<body>
  <header>
    <h1>Zohár – Kezdőbarát Gondolattérkép</h1>
    <span class="hint">Kattints bármelyik témakör szövegére a részletes magyarázathoz, a körre az ág nyitásához!</span>
  </header>
  <div id="container">
    <svg id="mindmap"></svg>
  </div>

  <aside id="detail-panel" aria-hidden="true">
    <div class="panel-header">
      <div>
        <div class="breadcrumb" id="panel-path"></div>
        <h2 id="panel-title">Témakör</h2>
      </div>
      <button id="close-btn" title="Bezárás">&times;</button>
    </div>
    <div class="panel-body">
      <div class="section-card">
        <h3>1. Miről szól ez a téma?</h3>
        <p id="panel-intro"></p>
      </div>
      <div class="section-card">
        <h3>2. Mi a belső, szellemi üzenete?</h3>
        <p id="panel-inner"></p>
      </div>
      <div class="section-card">
        <h3>3. Hogyan kapcsolódik a többi részhez?</h3>
        <p id="panel-connection"></p>
      </div>
    </div>
  </aside>

  <script>
    const nodeLookup = new Map();

    function buildMarkdown(node, depth = 1, path = []) {
      const currentPath = [...path, node.title];
      nodeLookup.set(node.title.trim(), {
        path: currentPath.join(' › '),
        summary: node.summary
      });
      const prefix = depth <= 6 ? '#'.repeat(depth) : '  '.repeat(depth - 6) + '-';
      let md = `${prefix} ${node.title}\\n\\n`;
      if (Array.isArray(node.children)) {
        for (const child of node.children) {
          md += buildMarkdown(child, depth + 1, currentPath);
        }
      }
      return md;
    }

    function openPanel(title) {
      const data = nodeLookup.get(title.trim());
      if (!data) return;
      document.getElementById('panel-title').textContent = title;
      document.getElementById('panel-path').textContent = data.path;
      document.getElementById('panel-intro').textContent = data.summary?.intro || '';
      document.getElementById('panel-inner').textContent = data.summary?.inner_meaning || '';
      document.getElementById('panel-connection').textContent = data.summary?.connection || '';
      document.getElementById('detail-panel').classList.add('open');
    }

    document.getElementById('close-btn').addEventListener('click', () => {
      document.getElementById('detail-panel').classList.remove('open');
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') document.getElementById('detail-panel').classList.remove('open');
    });

    fetch('zohar_summaries.json?v=' + Date.now())
      .then(res => res.json())
      .then(tree => {
        const md = buildMarkdown(tree);
        const transformer = new markmap.Transformer();
        const { root } = transformer.transform(md);
        markmap.Markmap.create('#mindmap', { initialExpandLevel: 2, duration: 400 }, root);

        document.getElementById('mindmap').addEventListener('click', (e) => {
          const fo = e.target.closest('foreignObject');
          if (fo) {
            const text = fo.textContent.trim();
            if (nodeLookup.has(text)) {
              openPanel(text);
            }
          }
        });

        openPanel(tree.title);
      });
  </script>
</body>
</html>
"""


def find_docx() -> Path:
    candidates = [
        Path("Zohár.docx"),
        Path("input/Zohár.docx"),
        Path("../Zohár.docx"),
        Path("../input/Zohár.docx"),
    ]
    for p in candidates:
        if p.exists():
            return p
    for p in Path(".").rglob("*Zoh*r*.docx"):
        return p
    raise FileNotFoundError("Nem található a Zohár.docx fájl a projektmappában vagy az input/ mappában.")


def read_docx_text(path: Path) -> str:
    doc = Document(path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def backup_existing_files():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backup") / stamp
    for fname in ["index.html", "zohar_summaries.json"]:
        src = Path(fname)
        if src.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, backup_dir / fname)
            print(f"Biztonsági mentés készült: {backup_dir / fname}")


def generate_tree(source_text: str) -> dict:
    client = genai.Client()
    prompt = (
        "Elemezd mélyrehatóan az alábbi Zohár forrásszöveget, és készítsd el belőle "
        "a kezdőbarát gondolattérkép teljes JSON struktúráját:\n\n"
        f"{source_text}"
    )

    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.4,
            thinking_config=types.ThinkingConfig(thinking_budget=8192),
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
    except Exception:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.4,
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )

    return json.loads(response.text)


def count_nodes(node: dict) -> int:
    return 1 + sum(count_nodes(c) for c in node.get("children", []))


def main():
    docx_path = find_docx()
    print(f"Forrás betöltése: {docx_path.resolve()}")
    text = read_docx_text(docx_path)
    print(f"Beolvasott szöveg hossza: {len(text)} karakter. Elemzés indítása ({MODEL_NAME})...")

    tree_data = generate_tree(text)
    backup_existing_files()

    Path("zohar_summaries.json").write_text(
        json.dumps(tree_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path("index.html").write_text(HTML_TEMPLATE, encoding="utf-8")

    print(f"Kész! Létrehozott csomópontok száma: {count_nodes(tree_data)}")
    print("Frissített fájlok: zohar_summaries.json, index.html")


if __name__ == "__main__":
    main()
