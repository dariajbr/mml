# File Format Guide

Detailed extraction strategies for every supported raw document format.

Before full extraction, follow the
[large-source preflight and splitting guidance](large-sources.md) in
`references/large-sources.md`. Never read an oversized source fully merely to
decide whether it is oversized. Every split must be logged before context
compaction, and extraction must resume from the log and manifest one chunk at a
time.

## Table of Contents

- [PDF](#pdf)
- [DOCX / Word](#docx--word)
- [TXT](#txt)
- [Markdown](#markdown)
- [HTML / Web](#html--web)
- [Image (whiteboard, photo)](#image-whiteboard-photo)
- [Audio](#audio)
- [URL](#url)

---

## PDF

**Primary library:** `PyMuPDF` (`fitz`)

### Text Extraction

```python
import fitz

def extract_pdf_text(pdf_path):
    """Extract text from PDF, preserving page structure."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        pages.append({"page": page_num, "text": text})
    doc.close()
    return pages
```

**Multi-column PDFs:** PyMuPDF's `get_text()` usually respects reading order.
If columns are extracted out of order, use blocks:

```python
blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
blocks.sort(key=lambda b: (b[1], b[0]))  # sort by y, then x
```

**Scanned PDFs (no text layer):** Use OCR. Options:
1. `pytesseract` + `pdf2image` (local, free)
2. Vision model read of rendered pages (if available)

Detect the source language or use the student's/source's language, then pass
the matching installed Tesseract language code. The following is an explicit
English example:

```python
from pdf2image import convert_from_path
import pytesseract

images = convert_from_path(pdf_path, dpi=300)
text = "\n\n".join(
    pytesseract.image_to_string(img, lang="eng")
    for img in images
)
```

### Image Extraction

See `scripts/extract_pdf_images.py` (embedded images) and
`scripts/render_pdf_page.py` (page renders) in the wiki-media-pipeline skill.

**When to render vs extract embedded:**

| Scenario | Method |
|---|---|
| Vector diagrams, standalone figures | `extract_pdf_images.py` |
| Tables with complex formatting | `render_pdf_page.py` |
| Text+figure composites | `render_pdf_page.py` |
| Photographs embedded in PDF | `extract_pdf_images.py` |
| Equations / formulas | `render_pdf_page.py` at 300 DPI |

### Edge Cases

- **Password-protected PDFs:** `doc.authenticate(password)` before reading
- **Corrupted PDFs:** Wrap in try/except, fallback to `pdftotext` (poppler)
- **Large PDFs:** Complete the large-source preflight first, then extract only
  the planned page ranges in chunks to avoid memory issues

---

## DOCX / Word

**Primary library:** `python-docx`

### Read Directly — Do Not Convert to PDF

DOCX contains structured information that PDF conversion destroys:
- Tracked changes (accept/reject history)
- Comments and annotations
- Revision marks
- Hyperlink metadata
- Table cell structure
- Heading level hierarchy

Read DOCX natively:

```python
from docx import Document

def extract_docx_text(docx_path):
    """Extract text from DOCX preserving heading structure."""
    doc = Document(docx_path)
    
    sections = []
    current_heading = None
    current_body = []
    
    for para in doc.paragraphs:
        if para.style.name.startswith('Heading'):
            if current_heading or current_body:
                sections.append({
                    "heading": current_heading,
                    "body": "\n".join(current_body)
                })
            current_heading = para.text
            current_body = []
        else:
            current_body.append(para.text)
    
    # Don't forget the last section
    if current_heading or current_body:
        sections.append({
            "heading": current_heading,
            "body": "\n".join(current_body)
        })
    
    return sections
```

### Tables in DOCX

```python
def extract_docx_tables(docx_path):
    """Extract tables from DOCX as structured data."""
    doc = Document(docx_path)
    tables = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        tables.append(rows)
    return tables
```

Preserve tables as markdown:

```python
def table_to_markdown(rows):
    """Convert table rows to markdown table."""
    if not rows:
        return ""
    lines = ["| " + " | ".join(row) + " |" for row in rows]
    # Insert separator after header
    if len(rows) > 1:
        sep = "| " + " | ".join(["---"] * len(rows[0])) + " |"
        lines.insert(1, sep)
    return "\n".join(lines)
```

### Comments and Tracked Changes

If the DOCX contains tracked changes or comments, preserve them:

```python
from docx.opc.constants import RELATIONSHIP_TYPE as RT

def extract_docx_comments(docx_path):
    """Extract comments from DOCX."""
    doc = Document(docx_path)
    # Comments are in word/comments.xml
    # Access via doc.part.related_parts by relationship type
    comments = []
    try:
        for rel in doc.part.rels.values():
            if "comments" in rel.reltype:
                comments_part = rel.target_part
                # Parse XML for comment text
                # ...
    except:
        pass
    return comments
```

When tracked changes exist, preserve them in the student's/source's language:
`[tracked change in the original: "previous text" → "revised text"]`.

### Fallback: Convert to PDF

Only use when `python-docx` fails to capture complex formatting:

```python
import subprocess

def docx_to_pdf(docx_path, output_dir):
    """Convert DOCX to PDF using LibreOffice (headless)."""
    subprocess.run([
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", output_dir, docx_path
    ], check=True, capture_output=True)
    # Returns path to generated PDF
```

**When to use fallback:**
- Complex embedded objects (Excel charts, PowerPoint slides)
- Heavy formatting that `python-docx` misreads
- Password-protected or corrupted DOCX files
- Documents with complex footnotes/endnotes that need exact positioning

---

## TXT

**Method:** Native file read.

```python
def read_txt(path):
    """Read text file with encoding detection."""
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path}")
```

**Preserve line breaks** for block quotes, poetry, structured notes.
Do not normalize all whitespace — `\n\n` may separate paragraphs intentionally.

---

## Markdown

**Method:** Native file read + frontmatter parsing.

```python
import re

def read_md(path):
    """Read markdown file, separate frontmatter and body."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract YAML frontmatter
    frontmatter = {}
    body = content
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if match:
        import yaml
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
    
    return {"frontmatter": frontmatter, "body": body}
```

When ingesting existing `.md` files, merge their content into the wiki
structure rather than copying verbatim. Update frontmatter to match wiki schema.

---

## HTML / Web

**Primary library:** `trafilatura` (best content extraction)

```python
import trafilatura

def extract_html(url_or_path):
    """Extract main content from HTML."""
    if url_or_path.startswith("http"):
        downloaded = trafilatura.fetch_url(url_or_path)
    else:
        with open(url_or_path, "r", encoding="utf-8") as f:
            downloaded = f.read()
    
    result = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        include_images=True,
        include_links=True,
        output_format="markdown"
    )
    return result
```

**Fallback:** `BeautifulSoup` for manual extraction

```python
from bs4 import BeautifulSoup

def extract_html_bs4(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    # Remove scripts, styles, nav
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    
    # Get main content (heuristic)
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
    return main.get_text("\n\n") if main else soup.get_text("\n\n")
```

---

## Image (whiteboard, photo)

**Method:** Vision model transcription + image preservation. Transcribe in the
detected language or the student's/source's language, and retain uncertain
markings instead of guessing.

```python
import os
import shutil

def process_image_source(image_path, wiki_root, source_slug):
    """Process an image source (whiteboard, handwritten notes)."""
    media_dir = f"{wiki_root}/media/uploaded"
    os.makedirs(media_dir, exist_ok=True)
    
    # Copy original to media
    ext = os.path.splitext(image_path)[1]
    dest = f"{media_dir}/{source_slug}{ext}"
    shutil.copy2(image_path, dest)
    
    # Transcribe via vision model (agent does this)
    # ... produces transcription text ...
    
    return {
        "media_path": dest,
        # "transcription": transcription_text
    }
```

See wiki-media-pipeline skill for optimization of the image file. When linking
to the preserved image, compute a document-relative path from the linking page.

---

## Audio

**Method:** Whisper transcription with automatic language detection or an
explicit language code matching the student's/source's language.

```python
import whisper

def transcribe_audio(audio_path, model="base", language=None):
    """Transcribe audio, detecting its language unless one is supplied."""
    model = whisper.load_model(model)
    result = model.transcribe(audio_path, language=language)
    return result["text"]
```

Model size trade-offs:

| Model | Speed | Quality | Use Case |
|---|---|---|---|
| `tiny` | ~10x realtime | acceptable | quick drafts, long recordings |
| `base` | ~7x realtime | good | standard choice |
| `small` | ~4x realtime | very good | important interviews |
| `medium` | ~2x realtime | excellent | key sources |
| `large` | ~1x realtime | best | final review of critical content |

After transcription, save the `.txt` file to `raw/` and process it as a
standard text source. Preserve the original audio file alongside it.

---

## URL

**Method:** Fetch + `trafilatura` extraction.

```python
import trafilatura

def extract_url(url):
    """Extract article content from a URL."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Failed to fetch {url}")
    
    result = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        include_images=True,
        output_format="markdown",
        url=url
    )
    return {
        "title": trafilatura.extract_metadata(downloaded).title,
        "content": result,
        "source_url": url
    }
```

Save the raw HTML alongside the extracted text in `raw/` for auditability.
