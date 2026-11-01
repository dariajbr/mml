# Wiki Media Schema Reference

## Directory Structure

Create `uploaded/` and `shared/` only when needed:

```
wiki/
├── media/
│   ├── extracted/                 # automatically extracted from source documents
│   │   └── {source-slug}/         # one folder per source document
│   │       ├── fig-*.png          # diagrams and figures
│   │       ├── chart-*.png        # data visualizations
│   │       ├── table-*.png        # tabular data images
│   │       ├── map-*.png          # maps and spatial diagrams
│   │       └── page-*-render.png  # full page renders
│   ├── uploaded/                  # manually added by users, when needed
│   │   ├── whiteboard-*.jpg
│   │   ├── event-*.jpg
│   │   └── photo-*.jpg
│   └── shared/                    # reused across multiple pages, when needed
│       └── *.png
```

Temporary extraction data belongs outside `wiki/` in the configured `temp_root`.
Each source requires a `slug` matching `^[a-z0-9][a-z0-9-]*$`. Preflight rejects
invalid or duplicate slugs, canonical staging-target aliases, a canonical
`temp_root` equal to or inside `wiki_root`, and any canonical staging/media-output
equality or ancestor overlap. It also rejects pre-existing staging directories.
All checks finish before any source is processed or output directory is created.
Staging is created exclusively for the current run, resolved directly beneath
`temp_root`, and recursively removed only if this run created it.

## Image Type Classification

| Type | Prefix | Format | Max Width | Use Case |
|---|---|---|---|---|
| Diagram | `fig-` | PNG | 1200px | Conceptual diagrams, flowcharts, models |
| Chart | `chart-` | PNG | 1200px | Data visualizations, graphs |
| Table | `table-` | PNG | 1600px | Tabular data rendered as image |
| Map | `map-` | PNG | 1600px | Maps and spatial diagrams |
| Photo | `photo-` | JPEG | 1600px | Photographs, event images |
| Whiteboard | `whiteboard-` | JPEG | 1600px | Handwritten notes, sketches |
| Screenshot | `screenshot-` | PNG | 1200px | Interface captures, digital artifacts |
| Formula | `formula-` | PNG | 1200px | Mathematical notation |

## Batch Configuration Format

```json
{
  "wiki_root": "/absolute/path/to/wiki",
  "temp_root": "/absolute/path/to/temporary/media-staging",
  "sources": [
    {
      "path": "/absolute/path/to/source/document.pdf",
      "type": "pdf",
      "slug": "unique-source-identifier",
      "extract_mode": "embedded",
      "pages": null,
      "image_type": "diagram"
    }
  ]
}
```

### Top-Level Fields

| Field | Required | Type | Description |
|---|---|---|---|
| `wiki_root` | Yes | string | Path to the vault's `wiki/` directory |
| `temp_root` | No | string | Temporary staging outside `wiki/`; defaults to `.tmp/llm-wiki/media-staging/` beside the vault |
| `sources` | Yes | array | Source objects with unique `slug` values |

### Source Object Fields

| Field | Required | Type | Description |
|---|---|---|---|
| `path` | Yes | string | Absolute path to source file |
| `type` | Yes | string | `pdf`, `docx`, or `image` |
| `slug` | Yes | string | Unique identifier, used as folder name |
| `extract_mode` | PDF only | string | `embedded` (default) or `render` |
| `pages` | No | int[] | Specific pages to process; null = all |
| `image_type` | No | string | Classification hint for optimization |

### Source Type Examples

**PDF with embedded diagrams:**

```json
{
  "path": "/home/aly/sources/planning-guide.pdf",
  "type": "pdf",
  "slug": "planning-guide",
  "extract_mode": "embedded",
  "image_type": "diagram"
}
```

**PDF page render (formatted table):**

```json
{
  "path": "/home/aly/sources/course-catalog.pdf",
  "type": "pdf",
  "slug": "course-catalog",
  "extract_mode": "render",
  "pages": [4, 5],
  "image_type": "table"
}
```

**Word document with images:**

```json
{
  "path": "/home/aly/sources/workshop-notes.docx",
  "type": "docx",
  "slug": "workshop-notes-2026",
  "image_type": "photo"
}
```

**Whiteboard photo:**

```json
{
  "path": "/home/aly/sources/IMG_4521.jpg",
  "type": "image",
  "slug": "whiteboard-study-group-notes",
  "image_type": "whiteboard"
}
```

## Output Report Format

```json
{
  "wiki_root": "/path/to/wiki",
  "total_processed": 5,
  "total_errors": 0,
  "media": [
    {
      "source": "/path/to/source.pdf",
      "slug": "source-slug",
      "source_type": "pdf",
      "image_type": "diagram",
      "original": "/path/to/temporary/media-staging/source-slug/file.png",
      "optimized": "/path/to/wiki/media/extracted/source-slug/fig-name.png",
      "wiki_path": "media/extracted/source-slug/fig-name.png",
      "width": 1200,
      "height": 800,
      "bytes": 45678,
      "compression_ratio": 2.3
    }
  ]
}
```

`wiki_path` is vault-relative report metadata, without a leading slash. It is not
necessarily the correct literal link in a Markdown page. The agent must prefix
it with the number of `../` segments required to reach `wiki/` from the
referring file's directory.

For example, `wiki/topics/example.md` uses `../` plus the `wiki_path`; a page at
`wiki/topics/unit/example.md` uses `../../` plus the `wiki_path`; and
`wiki/index.md` uses the `wiki_path` unchanged.

## Markdown Reference Patterns

All examples below assume the referring page is directly inside `wiki/topics/`.
Adapt the relative prefix for other page locations and write visible text in the
language of the surrounding page.

### Standard Image

```markdown
![Descriptive alt-text](../media/extracted/{slug}/{filename})
```

### With Caption

```markdown
<figure>

![Circular diagram showing four stages of a project planning cycle](../media/extracted/planning-guide/fig-project-planning-cycle.png)

<figcaption>
Project planning cycle: identify goals, gather information, assign tasks, and review progress.
</figcaption>

</figure>
```

### Whiteboard (image + transcription)

```markdown
## Whiteboard Notes: Study Group

> **Original whiteboard:**
> ![Whiteboard notes showing a study group's planning steps](../media/uploaded/whiteboard-study-group-notes.jpg)

### Transcription

- **Choose a topic**
  - List shared questions
  - Agree on the session's scope
- **Plan the work**
  - Divide reading tasks
  - Set the next review date
```

## Large Local Media

Review file size and readability before adding optimized media to the
repository. Keep staging outside `wiki/`, remove unnecessary intermediate
images, and coordinate any repository storage policy with its maintainers. The
batch pipeline itself requires only local files and does not depend on a hosted
asset manager or runtime media service.
