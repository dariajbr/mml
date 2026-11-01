# Large-Source Inspection, Splitting, and Recovery

Use this procedure before reading a source fully. Inspection returns metadata,
not source text, so it must not be replaced by a full model-context read merely
to decide whether the source is large.

## Inspect and split

Run from the repository root:

```bash
python .agents/skills/raw-to-structured/scripts/source_file_chunks.py inspect "raw/source.pdf"
python .agents/skills/raw-to-structured/scripts/source_file_chunks.py split "raw/source.pdf" \
  --output-dir ".tmp/llm-wiki/source" \
  --max-chars 24000 \
  --reason "Source cannot safely fit with current instructions and relevant wiki pages"
```

Inspect first. Choose a smaller `max_chars` when the current context is crowded.
There is no universal file-byte threshold; split when uncertain. The safe size
depends on the instructions, related wiki pages, and other material already in
context.

Keep originals immutable. Write chunks and `manifest.json` only to
`.tmp/llm-wiki/{source-slug}/`, outside the vault and outside `wiki/`. Do not
copy chunks into raw source folders or treat them as synthesized wiki pages.
Images, audio, and other atomic formats are not text-splitting inputs; use their
format-specific handling instead.

The script refuses to overwrite an existing manifest. Read the manifest to find
the absolute chunk paths, source-unit ranges, and actual character counts.

## Log every split before compaction

Every split must be appended to `wiki/log.md`, even when no wiki content has
been changed yet. Never request context compaction immediately after an
unlogged split. Append the entry in the student's preferred language; this is
the English template:

```markdown
## [YYYY-MM-DD] split | `raw/source.pdf`
- Reason: the source cannot fit into context together with instructions and related wiki pages.
- Chunks created: N; maximum chunk size: 24000 characters.
- Manifest: `.tmp/llm-wiki/source/manifest.json`.
- Original source unchanged.
```

Tell the student the chunk count and manifest path, then ask in their preferred
language: “The source was split into N chunks and the operation was recorded in
`wiki/log.md`. May I compact the conversation context and continue one chunk at
a time?”

Continue only after approval. After compaction, read `wiki/log.md` and
`manifest.json` before processing source material. Process one chunk at a time
and track completed chunks and unresolved items. Do not load all chunks back
into the same context.

## Failure handling

On extraction or split failure, stop and report the limitation instead of
loading the whole source. Do not silently fall back to a full read, modify the
original, or claim that unprocessed chunks were ingested.
