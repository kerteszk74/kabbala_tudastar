(function () {
  "use strict";
  const LABEL = "Zohár mindenkinek - Rashbi | ";
  const LOCAL_PREVIEWS = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);
  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function sourceLink(chapter) {
    const url = new URL(chapter.source_url);
    if (url.protocol !== "https:" || url.hostname !== "kabbalahmedia.info" ||
        url.pathname !== `/en/sources/${chapter.id}`) {
      throw new Error("Érvénytelen Zohár-forráslink.");
    }
    const link = element("a", LABEL + chapter.title);
    link.href = url.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
  }
  function location(chapter, point) {
    return `${chapter.volume}. kötet · ` + (point.number == null
      ? "Nem számozott szöveg"
      : `${point.number}. pont${point.occurrence > 1 ? ` (${point.occurrence}. előfordulás)` : ""}`);
  }
  function create() {
    let metadataPromise, referencesPromise, searchPromise, nodeRequest = 0;
    const previews = new Map();
    const panel = document.querySelector("#panel-sources");
    const dialog = document.querySelector("#sources-dialog");
    const contents = document.querySelector("#sources-contents");
    const sourceStatus = document.querySelector("#sources-status");

    async function json(path, optional = false) {
      const response = await fetch("./data/" + path);
      if (optional && response.status === 404) return null;
      if (!response.ok) throw new Error(`Zohár-adatok: HTTP ${response.status} (${path})`);
      return response.json();
    }
    function metadata() {
      if (!metadataPromise) {
        metadataPromise = json("zohar_chapters_index.json").then(data => {
          if (data.version !== 3 || data.content_mode !== "metadata_only" || !Array.isArray(data.chapters) ||
              data.chapters.length !== data.stats.chapters || data.volumes.length !== 13) {
            throw new Error("Hiányos Zohár-fejezetindex.");
          }
          return data;
        }).catch(error => { metadataPromise = undefined; throw error; });
      }
      return metadataPromise;
    }
    function loadSearch() {
      if (!searchPromise) {
        searchPromise = Promise.all([metadata(), json("zohar_search_index.json")])
          .then(([chapters, index]) => window.ZoharSearch.create(index, chapters))
          .catch(error => { searchPromise = undefined; throw error; });
      }
      return searchPromise;
    }
    async function chapterText(chapter) {
      if (!LOCAL_PREVIEWS) return null;
      if (!previews.has(chapter.id)) {
        const request = json(chapter.preview_file, true).then(data => {
          if (data === null) return null;
          if (data.id !== chapter.id || !Array.isArray(data.points) ||
              data.points.length !== chapter.point_count || typeof data.preamble !== "string") {
            throw new Error(`Hiányos fejezetszöveg: ${chapter.title}`);
          }
          return data;
        }).catch(error => { previews.delete(chapter.id); throw error; });
        previews.set(chapter.id, request);
      }
      return previews.get(chapter.id);
    }
    async function fillPoint(result) {
      const chapter = await chapterText(result.chapter);
      if (chapter === null) return result;
      if (result.number == null) return { ...result, text: chapter.preamble };
      const point = chapter.points.find(point => point.id === result.id);
      if (!point) throw new Error(`Hiányzó pont: ${result.id}`);
      return { ...result, text: point.text };
    }
    function appendHighlight(target, text, terms, engine) {
      const wanted = new Set(terms);
      let end = 0;
      for (const match of text.matchAll(/[\p{L}\p{N}]+/gu)) {
        if (!engine.terms(match[0]).some(term => wanted.has(term))) continue;
        target.append(document.createTextNode(text.slice(end, match.index)));
        target.append(element("mark", match[0]));
        end = match.index + match[0].length;
      }
      target.append(document.createTextNode(text.slice(end)));
    }
    function resultCard(result, query = "", engine = null) {
      const article = element("article", undefined, "rag-result zohar-source");
      const heading = element("h4");
      heading.append(sourceLink(result.chapter));
      article.append(heading, element("small", location(result.chapter, result)));
      const snippet = element("p");
      snippet.dir = "auto";
      const terms = engine ? engine.terms(query) : [];
      const hasText = typeof result.text === "string";
      const text = hasText ? result.text : "Kulcsszavak: " + result.keywords.join(", ");
      let start = 0;
      if (engine && terms.length) {
        const wanted = new Set(terms);
        const match = [...text.matchAll(/[\p{L}\p{N}]+/gu)]
          .find(match => engine.terms(match[0]).some(term => wanted.has(term)));
        if (match) start = Math.max(0, match.index - 100);
      }
      const quote = (start ? "… " : "") + text.slice(start, start + 450)
        + (start + 450 < text.length ? " …" : "");
      if (engine) appendHighlight(snippet, quote, terms, engine);
      else snippet.textContent = quote;
      article.append(snippet);
      if (hasText) {
        const details = element("details");
        const full = element("p", result.text);
        full.dir = "auto";
        details.append(element("summary", "Részlet megtekintése"), full);
        article.append(details);
      } else {
        article.append(element("p", "A teljes szöveg a fenti hivatalos forráslinken olvasható.", "rag-hint"));
      }
      return article;
    }
    async function search(query, volume) {
      const engine = await loadSearch();
      const results = engine.search(query, volume);
      return Promise.all(results.map(fillPoint));
    }
    async function showNode(id) {
      const request = ++nodeRequest;
      panel.textContent = "Kapcsolódó forráshelyek betöltése…";
      try {
        if (!referencesPromise) {
          referencesPromise = json("zohar_node_references.json")
            .catch(error => { referencesPromise = undefined; throw error; });
        }
        const [index, refs] = await Promise.all([metadata(), referencesPromise]);
        if (refs.version !== 3 || refs.content_mode !== "metadata_only" ||
            refs.stats.book_sha256 !== index.stats.book_sha256 ||
            !Object.hasOwn(refs.references, id)) {
          throw new Error("A térkép és a forráshivatkozások indexe nem egyezik.");
        }
        const results = await Promise.all(refs.references[id].map(reference => {
          const uid = reference.split(":")[0];
          const chapter = index.chapters.find(chapter => chapter.id === uid);
          if (!chapter) throw new Error(`Ismeretlen fejezethivatkozás: ${uid}`);
          const keywords = refs.keywords?.[reference];
          if (!Array.isArray(keywords) || !keywords.every(word => typeof word === "string")) {
            throw new Error(`Hiányzó pontkulcsszavak: ${reference}`);
          }
          const [, number, occurrence] = reference.split(":");
          return fillPoint({ id: reference, number: Number(number), occurrence: Number(occurrence), chapter, keywords });
        }));
        if (request !== nodeRequest) return;
        panel.replaceChildren();
        panel.append(element("p", "Kulcsszavas forrásajánlások; nem ellenőrzött értelmezések.", "rag-hint"));
        if (!results.length) panel.append(element("p", "Ehhez a témához nincs megbízható kulcsszavas forráskapcsolat."));
        for (const result of results) panel.append(resultCard(result));
      } catch (error) {
        console.error("Zohár-hivatkozások:", error);
        if (request === nodeRequest) panel.textContent = `A forráshelyek nem tölthetők be: ${error.message}`;
      }
    }
    async function showChapter(details, chapter) {
      if (!details.open || details.dataset.loaded) return;
      const body = element("div", "Forrásadatok betöltése…");
      details.append(body);
      try {
        const data = await chapterText(chapter);
        const records = data === null
          ? (await loadSearch()).pointsForChapter(chapter.id)
          : data.points.length ? data.points : [{ number: null, text: data.preamble }];
        if (!records.length) throw new Error(`Hiányzó pontmetaadatok: ${chapter.title}`);
        body.replaceChildren();
        const description = record => typeof record.text === "string"
          ? record.text : "Kulcsszavak: " + record.keywords.join(", ");
        if (records[0].number == null) {
          const text = element("p", description(records[0]));
          text.dir = "auto";
          body.append(text);
        } else {
          const label = element("label", "Pont kiválasztása ");
          const select = element("select");
          select.setAttribute("aria-label", `${chapter.title} – pont`);
          for (const point of records) {
            const option = element("option", location(chapter, point));
            option.value = point.id;
            select.append(option);
          }
          const text = element("p", description(records[0]));
          text.dir = "auto";
          select.addEventListener("change", () => {
            text.textContent = description(records.find(point => point.id === select.value));
          });
          label.append(select);
          body.append(label, text);
        }
        if (data === null) {
          body.append(element("p", "Teljes szöveg csak helyi előnézetben; olvasás a fenti hivatalos forráslinken.", "rag-hint"));
        }
        details.dataset.loaded = "true";
      } catch (error) {
        console.error("Zohár-fejezet:", error);
        body.textContent = `Hiba: ${error.message}. Csukd össze, majd nyisd újra az előnézetet.`;
        details.addEventListener("toggle", () => body.remove(), { once: true });
      }
    }
    async function showContents() {
      dialog.showModal();
      sourceStatus.textContent = "Tartalomjegyzék betöltése…";
      try {
        const data = await metadata();
        if (!contents.childElementCount) {
          const fragment = document.createDocumentFragment();
          for (const volume of data.volumes) {
            const group = element("details", undefined, "source-volume");
            const chapters = data.chapters.filter(chapter => chapter.volume === volume.id);
            group.append(element("summary", `${volume.title} · ${chapters.length} fejezet`));
            const list = element("ul");
            for (const chapter of chapters) {
              const row = element("li");
              const range = chapter.point_range;
              row.append(sourceLink(chapter), element("small", range
                ? ` · ${range[0]}–${range[1]}. pont · ${chapter.point_count} számozott szöveghely`
                : " · Nem számozott szöveg"));
              row.append(element("div", chapter.path.slice(2, -1).join(" › "), "breadcrumb"));
              const preview = element("details");
              preview.append(element("summary", LOCAL_PREVIEWS ? "Részlet megtekintése" : "Pontok és kulcsszavak"));
              preview.addEventListener("toggle", () => showChapter(preview, chapter));
              row.append(preview);
              list.append(row);
            }
            group.append(list);
            fragment.append(group);
          }
          contents.append(fragment);
        }
        sourceStatus.textContent = `${data.stats.volumes} kötet · ${data.stats.chapters} fejezet · ${data.stats.points.toLocaleString("hu")} számozott szöveghely`;
      } catch (error) {
        console.error("Zohár-tartalomjegyzék:", error);
        sourceStatus.textContent = `Hiba: ${error.message}`;
      }
    }
    async function fillVolumes() {
      const select = document.querySelector("#rag-volume");
      try {
        const data = await metadata();
        for (const volume of data.volumes) {
          const option = element("option", volume.title);
          option.value = String(volume.id);
          select.append(option);
        }
      } catch (error) {
        console.error("Zohár-kötetszűrő:", error);
        document.querySelector("#rag-status").textContent = `A kötetszűrő nem tölthető be: ${error.message}`;
      }
    }
    document.querySelector("#sources-open").addEventListener("click", showContents);
    document.querySelector("#sources-close").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => document.querySelector("#sources-open").focus());
    fillVolumes();
    return { loadSearch, search, resultCard, showNode };
  }
  window.ZoharLibrary = { create };
})();
