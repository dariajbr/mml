---
name: raw-to-structured
description: >
  Use when ingesting, extracting, or restructuring source materials into an
  existing Markdown knowledge base, including PDF, DOCX, TXT, MD, HTML, image,
  and audio sources with text, tables, citations, or visual material.
---

# Raw-to-Structured Knowledge Base Ingestion

Turn source material into attributed, interlinked Markdown pages while
preserving the original, student edits, ambiguity, and visual evidence.

## Required Workflow

Follow these steps in order.

1. **Read the confirmed structure.** Read `AGENTS.md` and use the schema in
   its `<!-- WIKI_STRUCTURE:CONFIRMED -->` block. If that block is absent, use
   SETUP rather than inventing pages or folders.
2. **Classify the input and targets.** Identify the source format, language,
   media, and existing or new target pages allowed by the confirmed schema.
3. **Run large-source preflight.** Before full reading, follow the preflight in
   [references/large-sources.md](references/large-sources.md). Do not read an
   oversized source fully merely to determine its size. Log every split in
   `wiki/log.md` before requesting compaction, then recover from that log and
   the manifest after approval.
4. **Extract without altering the original.** Use the format-specific guidance
   in [references/file-format-guide.md](references/file-format-guide.md), keep
   the original immutable, and retain page, section, or timestamp locators.
5. **Process visual material.** Invoke `wiki-media-pipeline` whenever images,
   diagrams, scans, or other visual material exist. Preserve complex tables as
   tables or page images rather than flattening them into prose.
6. **Map content to the schema.** Identify concepts, domain entities, sources,
   comparisons, hubs, and optional cases only where the confirmed schema
   supports them. Use the building blocks in
   [references/page-types.md](references/page-types.md) without treating their
   folders or fields as mandatory.
7. **Integrate conservatively.** Read every target page first and merge new
   material into its existing structure. Never overwrite student edits; retain
   existing content and update only the relevant sections and metadata.
8. **Preserve the evidence.** Attribute every claim to its source, preserve
   tables and ambiguity, present conflicting accounts with attribution, and
   never fabricate citations or missing bibliographic details.
9. **Connect and record the work.** Use document-relative `.md` page and media
   links as described in
   [references/obsidian-markdown.md](references/obsidian-markdown.md). Add
   backlinks, update `wiki/index.md`, and append an entry to `wiki/log.md`.

## Link Convention

Resolve links from the document containing them, include the `.md` filename,
and use descriptive alt text for media.

```markdown
<!-- From wiki/index.md -->
[Example concept](topics/example-concept.md)

<!-- From wiki/sources/example-source.md -->
[Example concept](../topics/example-concept.md)
[Example entity](../entities/example-entity.md)
```

For example, a student choosing International Relations Theory might map theorists to `entities/` and theories to `topics/`; another topic can use entirely different categories.
