const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const search = require("../assets/zohar_search.js");
const root = path.resolve(__dirname, "..");
const read = file => JSON.parse(fs.readFileSync(path.join(root, "docs", "data", file), "utf8"));
const chapters = read("zohar_chapters_index.json");
const index = read("zohar_search_index.json");
const engine = search.create(index, chapters);

test("the Pages package has only relative local paths and assets below 15 MB", () => {
  const docs = path.join(root, "docs");
  assert.ok(fs.existsSync(path.join(docs, ".nojekyll")));
  assert.ok(fs.existsSync(path.join(root, ".nojekyll")));
  const manifest = JSON.parse(fs.readFileSync(path.join(docs, "web_assets_manifest.json"), "utf8"));
  assert.deepEqual(manifest, JSON.parse(fs.readFileSync(path.join(root, "web_assets_manifest.json"), "utf8")));
  assert.equal(manifest.content_mode, "metadata_only");
  assert.equal(manifest.files.length, 7);
  const crypto = require("node:crypto");
  for (const file of manifest.files) {
    assert.ok(!file.path.startsWith("/"), file.path);
    assert.ok(!file.path.includes("/chapters/"), file.path);
    const bytes = fs.readFileSync(path.join(docs, ...file.path.split("/")));
    assert.equal(bytes.length, file.bytes);
    assert.ok(file.bytes < 15_000_000, file.path);
    assert.equal(crypto.createHash("sha256").update(bytes).digest("hex"), file.sha256);
    assert.deepEqual(bytes, fs.readFileSync(path.join(root, ...file.path.split("/"))));
  }
  const html = fs.readFileSync(path.join(docs, "index.html"), "utf8");
  assert.ok(!/(?:src|href)\s*=\s*["']\/(?!\/)/.test(html));
  assert.ok(!/fetch\(\s*["'`]\/(?!\/)/.test(html));
  for (const file of ["zohar_search.js", "zohar_library.js"]) {
    const source = fs.readFileSync(path.join(docs, "assets", file), "utf8");
    assert.ok(!/fetch\(\s*["'`]\/(?!\/)/.test(source), file);
  }
});

test("the complete corpus and original count are both verified", () => {
  assert.equal(chapters.volumes.length, 13);
  assert.equal(chapters.chapters.length, 2165);
  assert.equal(index.stats.points, 23555);
  assert.equal(index.stats.raw_line_point_markers, 23484);
  assert.equal(index.stats.direction_marker_points, 71);
  assert.equal(index.documents.length, 23555 + index.stats.unnumbered_chapters);
  assert.ok(fs.statSync(path.join(root, "docs", "data", "zohar_search_index.json")).size < 6_000_000);
});

test("Hungarian queries retrieve the same points as their English synonyms", () => {
  for (const [hu, en] of [
    ["fény", "light"], ["edény", "vessel"], ["kli", "vessel"],
    ["teremtő", "creator"], ["akarat", "will"], ["vágy", "desire"],
    ["képernyő", "screen"], ["visszaverődő fény", "reflected light"],
    ["teremtés célja", "purpose of creation"]
  ]) {
    const actual = engine.search(hu).map(result => result.id);
    assert.ok(actual.length > 0, hu);
    assert.deepEqual(actual, engine.search(en).map(result => result.id), hu);
  }
  assert.deepEqual(engine.search("vagy"), []);
  assert.notDeepEqual(engine.terms("kli"), engine.terms("klipot"));
});

test("every volume can be searched without leaking other-volume results", () => {
  for (let volume = 1; volume <= 13; volume++) {
    const chapter = chapters.chapters.find(chapter => chapter.volume === volume);
    const results = engine.search(chapter.title, String(volume), 5);
    assert.ok(results.length > 0, chapter.title);
    assert.ok(results.every(result => result.chapter.volume === volume));
  }
});

test("all public point IDs resolve to original numbers and official chapter URLs", () => {
  const ids = new Set();
  let count = 0;
  for (const chapter of chapters.chapters) {
    const points = engine.pointsForChapter(chapter.id);
    const numbered = points.filter(point => point.number !== null);
    assert.equal(numbered.length, chapter.point_count);
    const url = new URL(chapter.source_url);
    assert.equal(url.host, "kabbalahmedia.info");
    assert.equal(url.pathname, `/en/sources/${chapter.id}`);
    for (const point of numbered) {
      assert.equal(point.id, `${chapter.id}:${point.number}:${point.occurrence}`);
      assert.equal(point.text, undefined);
      assert.ok(Array.isArray(point.keywords));
      assert.ok(!ids.has(point.id));
      ids.add(point.id);
      count++;
    }
  }
  assert.equal(count, 23555);
  const byId = new Map(index.documents.map(document => [document[3], document]));
  for (const id of ids) assert.ok(byId.has(id));
  const refs = read("zohar_node_references.json");
  assert.equal(Object.keys(refs.references).length, 779);
  for (const references of Object.values(refs.references)) {
    for (const id of references) {
      assert.ok(ids.has(id), id);
      const position = index.documents.findIndex(document => document[3] === id);
      assert.deepEqual(refs.keywords[id], index.keywords[position]);
    }
  }
});

test("public indexes contain only metadata and unordered keyword postings", () => {
  assert.deepEqual(Object.keys(index).sort(), [
    "content_mode", "documents", "keywords", "lengths", "postings", "prefixes",
    "stats", "stopwords", "synonyms", "version"
  ]);
  assert.equal(index.version, 3);
  assert.equal(index.content_mode, "metadata_only");
  assert.deepEqual(Object.keys(chapters).sort(), ["chapters", "content_mode", "stats", "version", "volumes"]);
  for (const chapter of chapters.chapters) {
    assert.deepEqual(Object.keys(chapter).sort(), [
      "id", "language", "path", "point_count", "point_range", "preview_file", "source_url", "title", "volume"
    ]);
  }
  for (const document of index.documents) assert.equal(document.length, 4);
  for (const words of index.keywords) {
    assert.ok(words.length <= 8);
    assert.equal(new Set(words).size, words.length);
    for (const word of words) assert.ok(Object.hasOwn(index.postings, word), word);
  }
  for (const [word, postings] of Object.entries(index.postings)) {
    assert.match(word, /^[\p{L}\p{N}]+$/u);
    assert.match(postings, /^[0-9a-z]+(?:\.[0-9a-z]+)*$/);
  }
  assert.ok(!fs.existsSync(path.join(root, "docs", "data", "chapters", chapters.chapters[0].id + ".json")));
  const result = engine.search("visszaverődő fény")[0];
  assert.ok(result.keywords.includes("reflected"));
  assert.ok(result.keywords.includes("light"));
  assert.equal(result.text, undefined);
});

test("mixed-generation search data is rejected instead of showing wrong references", () => {
  assert.throws(() => search.create({ ...index, version: 1 }, chapters));
  assert.throws(() => search.create({
    ...index, stats: { ...index.stats, book_sha256: "wrong" }
  }, chapters));
  assert.throws(() => search.create({ ...index, keywords: [] }, chapters));
  assert.deepEqual(search.decode("0.1.z"), [0, 1, 36]);
  assert.deepEqual(engine.search("notarealzoharword_9384798"), []);
});

function libraryFixture(hostname, chapterStatus = 200) {
  const requests = [];
  const node = () => ({ append() {}, addEventListener() {}, setAttribute() {} });
  const context = {
    window: { location: { hostname }, ZoharSearch: search },
    document: { querySelector: node, createElement: node },
    URL, console,
    fetch: async url => {
      requests.push(url);
      let data, status = 200;
      if (url.includes("/chapters/")) {
        status = chapterStatus;
        const id = path.basename(url, ".json");
        data = { id, preamble: "Local-only fixture passage.",
          points: engine.pointsForChapter(id).filter(point => point.number !== null)
            .map(point => ({ ...point, text: "Local-only fixture passage." })) };
      } else {
        data = read(path.basename(url));
      }
      return { status, ok: status === 200, json: async () => data };
    }
  };
  require("node:vm").runInNewContext(
    fs.readFileSync(path.join(root, "assets", "zohar_library.js"), "utf8"), context
  );
  return { library: context.window.ZoharLibrary.create(), requests };
}

test("public hosts never request chapter text even if it is available", async () => {
  for (const host of ["kerteszk74.github.io", "localhost.example"]) {
    const { library, requests } = libraryFixture(host);
    const results = await library.search("fény", "2");
    assert.ok(results.length > 0);
    assert.ok(results.every(result => result.text === undefined && result.keywords.length > 0));
    assert.ok(!requests.some(url => url.includes("/chapters/")));
  }
});

test("only loopback hosts load available local full-text previews", async () => {
  for (const host of ["localhost", "127.0.0.1", "[::1]"]) {
    const { library, requests } = libraryFixture(host);
    const results = await library.search("fény", "2");
    assert.ok(results.length > 0);
    assert.ok(results.every(result => result.text === "Local-only fixture passage."));
    assert.ok(requests.some(url => url.includes("/chapters/")));
  }
});

test("missing local previews use metadata but server failures are reported", async () => {
  const missing = libraryFixture("localhost", 404);
  const results = await missing.library.search("fény", "2");
  assert.ok(results.length > 0);
  assert.ok(results.every(result => result.text === undefined && result.keywords.length > 0));
  const failed = libraryFixture("localhost", 503);
  await assert.rejects(failed.library.search("fény", "2"), /HTTP 503/);
});
