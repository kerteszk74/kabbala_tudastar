import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from docx import Document
from google import genai
from google.genai import types

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-4-carbon")
CHUNK_CHAR_LIMIT = 45000  # Kb. 25-35 oldalnyi szöveg szakaszonként
CACHE_FILE = Path("zohar_chunks_cache.json")

CHUNK_SYSTEM_PROMPT = """
Te a Kabbala és a Zohár autentikus, rendkívül közérthető tanítója vagy.
Egy 426 oldalas Zohár-mű egyik összefüggő szövegszakaszát kapod meg.
A feladatod, hogy ebből a szakaszból kinyerd az ÖSSZES lényeges tanítást, példázatot, fogalmat és összefüggést olyan olvasóknak, AKIK MOST ISMERKEDNEK A KABBALÁVAL.

Szabályok minden egyes csomóponthoz:
1. Ne hagyj ki fontos altémákat vagy példázatokat ebből a szakaszból! Készíts 1-3 főágat a szakasz fő témáiból, és mindegyikhez 3-5 részletes alágat (szükség esetén 3. szintű alágakat is).
2. Kerüld a megmagyarázatlan héber/arámi szakkifejezéseket! Ha szerepel egy alapfogalom (pl. Cimcum, Keli, Ór, Szefirák, Klipot, Rózsa, Maszah), azonnal fordítsd le hétköznapi magyar nyelvre és szemléletes hasonlatra.
3. Minden csomópont összefoglalója pontosan 3 mezőből álljon:
   - "intro": Miről szól ez a téma? (Világos, barátságos bevezető és hétköznapi analógia, 3-5 mondatban.)
   - "inner_meaning": Mi a belső, szellemi üzenete? (A vágyak működése, az adás és befogadás szándéka közérthetően, 3-5 mondatban.)
   - "connection": Hogyan kapcsolódik a könyv többi részéhez? (Miért következik ez az előző gondolatból, és milyen felismeréshez vezet tovább.)

Kizárólag érvényes JSON struktúrát adj vissza az alábbi formátumban:
{
  "branches": [
    {
      "title": "Témakör pontos, beszédes címe",
      "summary": {
        "intro": "...",
        "inner_meaning": "...",
        "connection": "..."
      },
      "children": [
        {
          "title": "Altéma címe",
          "summary": {
            "intro": "...",
            "inner_meaning": "...",
            "connection": "..."
          },
          "children": []
        }
      ]
    }
  ]
}
"""

ROOT_SYSTEM_PROMPT = """
Te a Kabbala és a Zohár közérthető tanítója vagy.
A feladatod, hogy a mellékelt témakör-lista alapján megírd a teljes 426 oldalas Zohár-gondolattérkép központi (gyökér) csomópontjának kezdőbarát bevezetőjét.

Kizárólag érvényes JSON-t adj vissza:
{
  "title": "Bevezetés a Zohár könyvéhez – Teljes Útmutató",
  "summary": {
    "intro": "...",
    "inner_meaning": "...",
    "connection": "..."
  }
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
      padding: 10px 18px;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .title-group { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    header h1 { font-size: 1.05rem; color: #38bdf8; font-weight: 600; }
    .badge {
      background: #0f172a;
      border: 1px solid #38bdf8;
      color: #38bdf8;
      font-size: 0.78rem;
      padding: 2px 8px;
      border-radius: 999px;
    }
    .controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    #search-input {
      background: #0f172a;
      border: 1px solid #475569;
      color: #f8fafc;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.85rem;
      width: 240px;
    }
    #search-input:focus { outline: none; border-color: #38bdf8; }
    #search-results {
      position: absolute;
      top: 52px;
      right: 18px;
      width: 340px;
      max-width: 90vw;
      max-height: 320px;
      overflow-y: auto;
      background: #1e293b;
      border: 1px solid #38bdf8;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.6);
      z-index: 90;
      display: none;
    }
    .search-item {
      padding: 9px 12px;
      border-bottom: 1px solid #334155;
      cursor: pointer;
      font-size: 0.85rem;
    }
    .search-item:hover { background: #334155; }
    .search-item small { display: block; color: #94a3b8; font-size: 0.74rem; margin-top: 2px; }
    header .hint { font-size: 0.8rem; color: #94a3b8; }
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
      right: -480px;
      width: 460px;
      max-width: 94vw;
      height: 100vh;
      background: #1e293b;
      border-left: 1px solid #38bdf8;
      box-shadow: -8px 0 24px rgba(0, 0, 0, 0.55);
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
    #panel-title { font-size: 1.2rem; color: #ffffff; line-height: 1.3; }
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
      font-size: 0.95rem;
    }
    .section-card {
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 14px;
    }
    .section-card h3 {
      font-size: 0.88rem;
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
    <div class="title-group">
      <h1>Zohár – Kezdőbarát Gondolattérkép</h1>
      <span class="badge" id="node-count">Betöltés...</span>
      <span class="hint">Kattints a szövegre a magyarázathoz, a körre a nyitáshoz!</span>
    </div>
    <div class="controls">
      <input type="text" id="search-input" placeholder="Keresés a témák között..." autocomplete="off" />
    </div>
  </header>
  <div id="search-results"></div>

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
        title: node.title.trim(),
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
      document.getElementById('panel-title').textContent = data.title;
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
      if (e.key === 'Escape') {
        document.getElementById('detail-panel').classList.remove('open');
        document.getElementById('search-results').style.display = 'none';
      }
    });

    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');

    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      if (q.length < 2) {
        searchResults.style.display = 'none';
        return;
      }
      const matches = [];
      for (const item of nodeLookup.values()) {
        const hay = (item.title + ' ' + (item.summary?.intro || '') + ' ' + (item.summary?.inner_meaning || '')).toLowerCase();
        if (hay.includes(q)) matches.push(item);
      }
      searchResults.innerHTML = matches.slice(0, 25).map(m =>
        `<div class="search-item" data-title="${m.title.replace(/"/g, '&quot;')}">
          <strong>${m.title}</strong>
          <small>${m.path}</small>
        </div>`
      ).join('') || '<div class="search-item">Nincs találat</div>';
      searchResults.style.display = 'block';
    });

    searchResults.addEventListener('click', (e) => {
      const item = e.target.closest('.search-item');
      if (item && item.dataset.title) {
        openPanel(item.dataset.title);
        searchResults.style.display = 'none';
      }
    });

    fetch('zohar_summaries.json?v=' + Date.now())
      .then(res => res.json())
      .then(tree => {
        const md = buildMarkdown(tree);
        document.getElementById('node-count').textContent = `${nodeLookup.size} témakör`;
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
    for p in Path(".").glob("*zohar*.docx"):
        return p
    for p in Path(".").glob("*.docx"):
        return p
    raise FileNotFoundError("Nem található .docx fájl a mappában.")


def split_docx_into_chunks(path: Path, char_limit: int) -> list[str]:
    doc = Document(path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    chunks = []
    current = []
    current_len = 0

    for p in paragraphs:
        if current_len + len(p) > char_limit and current:
            chunks.append("\n\n".join(current))
            current = [p]
            current_len = len(p)
        else:
            current.append(p)
            current_len += len(p) + 2

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def call_gemini_json(client: genai.Client, system_prompt: str, user_prompt: str) -> dict:
    for attempt in range(3):
        try:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.35,
                    thinking_config=types.ThinkingConfig(thinking_budget=4096),
                )
                resp = client.models.generate_content(
                    model=MODEL_NAME, contents=user_prompt, config=config
                )
            except Exception:
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.35,
                )
                resp = client.models.generate_content(
                    model=MODEL_NAME, contents=user_prompt, config=config
                )
            return json.loads(resp.text)
        except Exception as e:
            print(f"  [Újrapróbálás {attempt + 1}/3] Hiba: {e}")
            time.sleep(4)
    raise RuntimeError("A Gemini API hívás 3 próbálkozás után sem sikerült.")


def deduplicate_titles(node: dict, seen: set[str]):
    base_title = node["title"].strip()
    title = base_title
    counter = 2
    while title in seen:
        title = f"{base_title} ({counter})"
        counter += 1
    node["title"] = title
    seen.add(title)
    for child in node.get("children", []):
        deduplicate_titles(child, seen)


def count_nodes(node: dict) -> int:
    return 1 + sum(count_nodes(c) for c in node.get("children", []))


def backup_existing_files():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backup") / stamp
    for fname in ["index.html", "zohar_summaries.json"]:
        src = Path(fname)
        if src.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, backup_dir / fname)


def main():
    docx_path = find_docx()
    print(f"Forrásfájl: {docx_path.name}")
    chunks = split_docx_into_chunks(docx_path, CHUNK_CHAR_LIMIT)
    total = len(chunks)
    print(f"A teljes dokumentum {total} részre bontva a mélyelemzéshez ({MODEL_NAME}).")

    cache = {}
    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        print(f"Korábbi mentett szakaszok betöltve: {len(cache)}/{total}")

    client = genai.Client()
    all_branches = []
    prev_topic = "A könyv nyitánya"

    for idx, chunk_text in enumerate(chunks, start=1):
        key = str(idx)
        if key in cache:
            print(f"[{idx}/{total}] Szakasz betöltve a gyorsítótárból.")
            branches = cache[key]
        else:
            print(f"[{idx}/{total}] Mélyelemzés folyamatban ({len(chunk_text)} karakter)...")
            prompt = (
                f"Ez a 426 oldalas könyv {idx}. szakasza (összesen {total} szakaszból). "
                f"Az előző szakasz záró témaköre: '{prev_topic}'.\n\n"
                f"Forrásszöveg:\n{chunk_text}"
            )
            data = call_gemini_json(client, CHUNK_SYSTEM_PROMPT, prompt)
            branches = data.get("branches", [])
            cache[key] = branches
            CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

        if branches:
            prev_topic = branches[-1].get("title", prev_topic)
            all_branches.extend(branches)

    print("Központi gyökér-összefoglaló generálása...")
    branch_titles = "\n".join(f"- {b['title']}" for b in all_branches)
    root_data = call_gemini_json(
        client,
        ROOT_SYSTEM_PROMPT,
        f"A feldolgozott fő témakörök listája:\n{branch_titles}",
    )

    tree = {
        "title": root_data.get("title", "Bevezetés a Zohár könyvéhez"),
        "summary": root_data.get("summary", {}),
        "children": all_branches,
    }
    deduplicate_titles(tree, set())

    backup_existing_files()
    Path("zohar_summaries.json").write_text(
        json.dumps(tree, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path("index.html").write_text(HTML_TEMPLATE, encoding="utf-8")

    print(f"\nSIKER! A teljes 426 oldalas forrásból {count_nodes(tree)} részletes csomópont készült.")
    print("Frissített fájlok: zohar_summaries.json, index.html")


if __name__ == "__main__":
    main()
