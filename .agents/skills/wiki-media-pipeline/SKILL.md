---
name: wiki-media-pipeline
description: >
  Media extraction, processing, and organization pipeline for local Markdown
  knowledge bases. Handles images from PDFs, Word documents, and photos;
  optimizes them for local Markdown readers; organizes them into semantic folder
  structures; and generates document-relative Markdown references. Use when:
  (1) extracting images from source materials (PDFs, DOCX, images), (2)
  processing or optimizing media files (resize, compress, convert formats),
  (3) organizing images into structured folder hierarchies, (4) generating
  Markdown image references with alt-text, (5) ingesting documents containing
  visual content into a Markdown knowledge base, or (6) handling whiteboard
  photos, diagrams, tables, or charts.
---

# Wiki Media Pipeline

Extract, process, organize, and reference images from documents for a local
Markdown knowledge base. Match the language of the surrounding content when
writing alt-text, captions, and transcriptions.

## Dependencies

Install on first use:

```bash
python3 -m pip install PyMuPDF Pillow python-docx pdf2image
```

For `pdf2image`, also install the system package that provides Poppler.

## Workflow Overview

Media ingestion follows these steps:

1. **Detect media sources** — scan the source document for embedded or attached images.
2. **Extract** — pull images into temporary staging outside `wiki/`.
3. **Inspect and classify** — use vision to understand each image's content.
4. **Name and organize** — move images into a semantic folder structure with descriptive names.
5. **Optimize** — resize and compress for local Markdown readers.
6. **Reference** — insert document-relative Markdown image links with alt-text.

## Step 1: Detect Sources

Determine the source type and extraction strategy:

| Source Type | Extraction Method | Script |
|---|---|---|
| PDF with embedded images | `PyMuPDF` (`fitz`) | `scripts/extract_pdf_images.py` |
| PDF page as image | `pdf2image` render | `scripts/render_pdf_page.py` |
| Word (.docx) | `python-docx` | `scripts/extract_docx_images.py` |
| Image files (.jpg, .png) | Direct copy | Manual |
| Photo (whiteboard, handwritten) | Direct copy | Manual |

## Step 2: Extract

Create temporary extraction data outside `wiki/`. The batch script accepts an
optional `temp_root`; by default it stages files in
`.tmp/llm-wiki/media-staging/` beside the vault. Keep original source files
unchanged.

### From PDF (embedded images)

```python
import fitz  # PyMuPDF

def extract_pdf_images(pdf_path, output_dir):
    """Extract all embedded images from a PDF file."""
    doc = fitz.open(pdf_path)
    extracted = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        for img_idx, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            ext = base_image["ext"]
            filename = f"page-{page_num+1}-fig-{img_idx+1}.{ext}"
            filepath = f"{output_dir}/{filename}"
            with open(filepath, "wb") as f:
                f.write(base_image["image"])
            extracted.append({
                "path": filepath,
                "page": page_num + 1,
                "index": img_idx + 1,
                "width": base_image["width"],
                "height": base_image["height"]
            })
    doc.close()
    return extracted
```

### From PDF (full page render)

Use when layout matters, such as text-and-diagram composites or formatted tables:

```python
from pdf2image import convert_from_path

def render_pdf_pages(pdf_path, output_dir, pages=None, dpi=200):
    """Render PDF pages as images. pages=None renders all."""
    kwargs = {"dpi": dpi}
    if pages:
        kwargs["first_page"] = pages[0]
        kwargs["last_page"] = pages[-1]
    images = convert_from_path(pdf_path, **kwargs)
    extracted = []
    for i, image in enumerate(images):
        page_num = pages[i] if pages else i + 1
        filepath = f"{output_dir}/page-{page_num}-render.png"
        image.save(filepath, "PNG")
        extracted.append({"path": filepath, "page": page_num})
    return extracted
```

### From Word (.docx)

```python
from docx import Document

def extract_docx_images(docx_path, output_dir):
    """Extract all images from a Word document."""
    doc = Document(docx_path)
    extracted = []
    image_parts = []
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_parts.append(rel.target_part)
    for idx, image_part in enumerate(image_parts):
        ext = image_part.content_type.split("/")[-1]
        filename = f"image-{idx+1}.{ext}"
        filepath = f"{output_dir}/{filename}"
        with open(filepath, "wb") as f:
            f.write(image_part.blob)
        extracted.append({"path": filepath, "index": idx + 1})
    return extracted
```

## Step 3: Inspect and Classify

After extraction, visually inspect every image. Determine:

- **Type**: `diagram` | `chart` | `table` | `map` | `photo` | `screenshot` | `whiteboard` | `formula`
- **Subject**: What does it depict, using wording appropriate to the subject area?
- **Relevance**: Which Markdown page or pages should reference this image?
- **Quality**: Is it readable? Does it need re-rendering at higher DPI?

Do not rely on filenames alone: an unclear or decorative image may need a better
render or no inclusion. For whiteboard photos, transcribe handwritten content
while preserving the original image.

## Step 4: Name and Organize

Move images from temporary staging into the vault's media structure. Create
`uploaded/` and `shared/` only when they are needed:

```
wiki/media/
├── extracted/                 # automatically extracted from source documents
│   └── {source-slug}/         # one folder per source
│       ├── fig-{descriptor}.{ext}
│       ├── chart-{descriptor}.{ext}
│       ├── table-{descriptor}.{ext}
│       └── map-{descriptor}.{ext}
├── uploaded/                  # manually added by users, when needed
│   └── {descriptor}.{ext}
└── shared/                    # reused across multiple pages, when needed
    └── {descriptor}.{ext}
```

Use `wiki/media/extracted/{source-slug}/` for extracted images,
`wiki/media/uploaded/` for manually supplied images, and `wiki/media/shared/`
for assets intentionally reused across pages.

**Naming convention:**

```
{type}-{descriptive-slug}.{ext}

Examples:
  fig-project-planning-cycle.png
  chart-monthly-reading-progress-2026.jpg
  table-course-comparison.png
  map-fieldwork-locations.png
  whiteboard-study-group-notes.jpg
```

Use lowercase, hyphenated source slugs derived from the source filename without
its extension. Keep descriptors meaningful and consistent with the vault's
naming conventions; alt-text, captions, and transcriptions should follow the
language of each referring page.

## Step 5: Optimize

Run `scripts/optimize_image.py` on each extracted image:

```python
from PIL import Image

def optimize_image(input_path, output_path, max_width=1200, quality=85):
    """Resize and compress an image for local Markdown readers."""
    img = Image.open(input_path)
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    ext = output_path.split(".")[-1].lower()
    if ext in ("jpg", "jpeg"):
        img.save(output_path, "JPEG", quality=quality, optimize=True)
    elif ext == "png":
        img.save(output_path, "PNG", optimize=True)
    return output_path
```

**Parameters by image type:**

| Type | Max Width | Format | Quality |
|---|---|---|---|
| Diagrams, charts | 1200px | PNG | — |
| Photos, whiteboards | 1600px | JPEG | 85 |
| Tables (text-heavy) | 1600px | PNG | — |
| Maps | 1600px | PNG | — |

Balance smaller files with legibility, especially for labels and handwriting.
The pipeline uses only local files and does not require a runtime media service.

## Step 6: Reference in Markdown

Use a document-relative link calculated from the referring Markdown file, not a
root-relative URL:

```markdown
![Descriptive alt-text explaining the image content](../media/extracted/{source-slug}/{filename})
```

For example, `wiki/topics/project-planning.md` references an image with
`../media/extracted/planning-guide/fig-project-planning-cycle.png`, while
`wiki/index.md` references the same image with
`media/extracted/planning-guide/fig-project-planning-cycle.png`. Add one `../`
segment for each directory level between the referring file and `wiki/`.

**Alt-text rules:**

- Describe what the image shows, not just "Figure 1".
- Include key labels, axes, or data points for charts.
- Mention the source if relevant.
- Keep it under 150 characters for accessibility.
- Use the language of the surrounding page.

**Examples for a page directly under `wiki/topics/`:**

```markdown
![Circular diagram showing four stages of a project planning cycle](../media/extracted/planning-guide/fig-project-planning-cycle.png)

![Table comparing three courses by duration, workload, and assessment format](../media/extracted/course-catalog/table-course-comparison.png)

![Whiteboard notes from a study group, showing the main planning steps](../media/uploaded/whiteboard-study-group-notes.jpg)
```

For whiteboard photos, include both the image and a transcription block in the
page's language.

## Complete Batch Pipeline

For processing multiple source documents at once, use
`scripts/process_media_batch.py`. See
[references/media-schema.md](references/media-schema.md) for the full
input/output schema and batch configuration format. Each source `slug` must
match `^[a-z0-9][a-z0-9-]*$`. Before creating directories or processing sources,
preflight rejects invalid or duplicate slugs, canonical staging-target aliases,
and pre-existing staging directories. Each run creates its staging directory
exclusively and removes only that newly created directory on success or failure.

The report's `wiki_path` is vault-relative metadata such as
`media/extracted/{source-slug}/{filename}`, without a leading slash. It is not a
ready-to-paste link: prefix it with the correct number of `../` segments for the
referring Markdown file.

## Large Local Media

Keep source files and temporary extraction data outside `wiki/`. Resize only
when the result remains readable, remove unneeded intermediate images, and
review unusually large files before adding them to the repository. If local
media makes the repository difficult to manage, agree on a storage policy with
the repository maintainers; no hosted asset manager or additional runtime
service is required by this pipeline.

## Handling Conflicts

When two users extract or optimize the same source image:

- Compare both versions using image metadata such as dimensions and file size.
- Prefer the higher-resolution or better-optimized readable version.
- If they are semantically different, such as different crops, rename them with suffixes like `-v1` and `-v2`.
- Flag unresolved differences for human review.
