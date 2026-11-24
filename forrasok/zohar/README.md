# Zohar for All - local source archive

The archive is created by `../../download_zohar_book.py` using the public
Kabbalah Media source catalogue and its official document-to-HTML service.
Starting page: https://kabbalahmedia.info/en/sources/yUcfylRm?source_language=en

Run from the workspace root:

```powershell
python .\download_zohar_book.py
```

- `zohar_teljes_konyv.md`: all 13 volumes in catalogue order, in one UTF-8 file.
- Each source article is included once: English preferred, otherwise Hebrew.
- Original paragraph numbers, titles, catalogue paths, and source URLs are kept.
- The raw line-start count is 23,484. The website index additionally recognizes
  71 numbered paragraphs preceded by invisible direction marks: 23,555 total.
  The original book and download manifest are unchanged; both counts are recorded
  in the generated index statistics.
- Where a catalogue article has no separate file, its section is recovered from
  the nearest complete official parent document using an exact, unique heading.
- Identical text is included only once, with cross-references for duplicate entries.
- Illustrations link to official online files; this is not an offline image archive.
- `zohar_letoltes_jegyzek.json`: per-article language, source, download URL,
  character count, paragraph-marker count, and SHA-256 integrity information.
- `.download_cache`: public catalogue, metadata, and article responses for resuming
  interrupted downloads. Remove this specific subdirectory to refresh the source.
- The final book is replaced only after every source entry has been processed.
  Missing English/Hebrew source text causes an explicit error, not a partial book.

The text remains the property of its respective rights holders (Kabbalah Media /
Bnei Baruch). The files are for local reference; no redistribution permission is
asserted. Source files and download caches are excluded from Git; only this
README is eligible for version control. The generated full-text chapter JSONs
in `data/chapters/` are local-only too; `docs/data/chapters/` is also excluded.
The public website publishes titles, paragraph numbers, unordered keyword
postings and official reader links, not the book text or paragraph quotations.
