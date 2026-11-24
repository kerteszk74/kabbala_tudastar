(function (root) {
  "use strict";
  function normalize(text) {
    return text.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
  }
  function tokenizer(config) {
    const aliases = new Map();
    for (const group of config.synonyms) {
      for (const alias of group) {
        if (normalize(alias) !== "vagy") aliases.set(normalize(alias), normalize(group[0]));
      }
    }
    const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const rules = [...aliases].filter(([alias, canonical]) => alias !== canonical)
      .sort((a, b) => b[0].length - a[0].length)
      .map(([alias, canonical]) => [
        new RegExp(`(?<![\\p{L}\\p{N}_])${escape(alias)}(?![\\p{L}\\p{N}_])`, "gu"), canonical
      ]);
    const stopwords = new Set(config.stopwords);
    return text => {
      text = normalize(text.toLowerCase().replace(/vágy[\p{L}]*/gu, " desire "));
      for (const [pattern, canonical] of rules) text = text.replace(pattern, canonical);
      return (text.match(/[\p{L}\p{N}]+/gu) || [])
        .filter(word => word.length > 1 && !stopwords.has(word))
        .map(word => Object.entries(config.prefixes).find(([prefix]) => word.startsWith(prefix))?.[1] || word);
    };
  }
  function decode(encoded) {
    let position = 0;
    return encoded.split(".").map(value => (position += parseInt(value, 36)));
  }
  function create(index, chapters) {
    if (index.version !== 3 || chapters.version !== 3 ||
        index.content_mode !== "metadata_only" || chapters.content_mode !== "metadata_only" ||
        index.stats.book_sha256 !== chapters.stats.book_sha256 ||
        index.documents.length !== index.stats.points + index.stats.unnumbered_chapters ||
        index.lengths.length !== index.documents.length ||
        !Array.isArray(index.keywords) || index.keywords.length !== index.documents.length ||
        !index.keywords.every(words => Array.isArray(words) && words.every(word => typeof word === "string"))) {
      throw new Error("Hibás vagy eltérő verziójú Zohár-keresőindex.");
    }
    const terms = tokenizer(index);
    const average = index.lengths.reduce((sum, size) => sum + size, 0) / index.lengths.length;
    function point(position) {
      const [chapterIndex, number, occurrence, id] = index.documents[position];
      return { id, number, occurrence, position, chapter: chapters.chapters[chapterIndex],
        keywords: index.keywords[position] };
    }
    function search(query, volume = "", limit = 12) {
      const words = [...new Set(terms(query))];
      const scores = new Map();
      const matched = new Map();
      for (const word of words) {
        const encoded = Object.hasOwn(index.postings, word) ? index.postings[word] : null;
        if (encoded == null) continue;
        const postings = decode(encoded);
        const inverse = Math.log(1 + index.documents.length / (1 + postings.length));
        for (const position of postings) {
          const chapter = chapters.chapters[index.documents[position][0]];
          if (volume !== "" && chapter.volume !== Number(volume)) continue;
          const weight = inverse / (0.5 + 0.5 * index.lengths[position] / average);
          scores.set(position, (scores.get(position) || 0) + weight);
          if (!matched.has(position)) matched.set(position, []);
          matched.get(position).push(word);
        }
      }
      return [...scores].sort((a, b) =>
        matched.get(b[0]).length - matched.get(a[0]).length || b[1] - a[1] || a[0] - b[0]
      ).slice(0, limit).map(([position, score]) => {
        return { ...point(position), score,
          keywords: [...new Set([...matched.get(position), ...index.keywords[position]])] };
      });
    }
    function pointsForChapter(id) {
      const positions = [];
      for (let position = 0; position < index.documents.length; position++) {
        if (chapters.chapters[index.documents[position][0]].id === id) positions.push(position);
      }
      return positions.map(point);
    }
    return { terms, search, pointsForChapter };
  }
  const api = { normalize, tokenizer, decode, create };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ZoharSearch = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
