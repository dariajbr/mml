#!/usr/bin/env python3
"""
Universal raw document reader for wiki ingestion.

Detects file type and extracts text + structure. Returns JSON with content
and metadata.

Usage:
    python read_source_file.py <file_path> [--output-json]

Output: JSON with keys: type, content (list of sections/pages), metadata
"""

import argparse
import json
import mimetypes
import os
import re
import subprocess

def detect_format(file_path):
    """Detect file format by extension and content inspection."""
    ext = os.path.splitext(file_path)[1].lower()
    mime, _ = mimetypes.guess_type(file_path)
    
    format_map = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".txt": "txt",
        ".md": "markdown",
        ".html": "html",
        ".htm": "html",
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".webp": "image",
        ".mp3": "audio",
        ".wav": "audio",
        ".m4a": "audio",
    }
    
    fmt = format_map.get(ext)
    if fmt:
        return fmt
    
    # Fallback: check MIME type
    if mime:
        if mime == "application/pdf":
            return "pdf"
        elif mime in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
            return "docx"
        elif mime.startswith("text/"):
            return "txt"
        elif mime.startswith("image/"):
            return "image"
        elif mime.startswith("audio/"):
            return "audio"
    
    return "unknown"


def read_pdf(file_path):
    """Extract text from PDF using PyMuPDF."""
    import fitz
    
    doc = fitz.open(file_path)
    pages = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text().strip()
        if text:
            pages.append({"page": page_num, "text": text})
    doc.close()
    
    return {
        "type": "pdf",
        "pages": pages,
        "total_pages": len(pages),
        "metadata": {
            "file": os.path.basename(file_path),
            "has_images": True  # PDFs typically need image extraction
        }
    }


def read_docx(file_path):
    """Extract text and structure from DOCX using python-docx."""
    from docx import Document
    
    doc = Document(file_path)
    
    # Extract paragraphs with style info
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append({
                "text": para.text,
                "style": para.style.name,
                "is_heading": para.style.name.startswith("Heading")
            })
    
    # Extract tables
    tables = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        tables.append(rows)
    
    # Build sections from headings
    sections = []
    current_heading = None
    current_body = []
    
    for para in paragraphs:
        if para["is_heading"]:
            if current_heading or current_body:
                sections.append({
                    "heading": current_heading,
                    "body": "\n".join(current_body)
                })
            current_heading = para["text"]
            current_body = []
        else:
            current_body.append(para["text"])
    
    if current_heading or current_body:
        sections.append({
            "heading": current_heading,
            "body": "\n".join(current_body)
        })
    
    return {
        "type": "docx",
        "sections": sections,
        "paragraphs": paragraphs,
        "tables": tables,
        "metadata": {
            "file": os.path.basename(file_path),
            "has_images": True,
            "heading_count": len([p for p in paragraphs if p["is_heading"]])
        }
    }


def read_txt(file_path):
    """Read text file with encoding detection."""
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            return {
                "type": "txt",
                "content": content,
                "metadata": {
                    "file": os.path.basename(file_path),
                    "encoding": encoding,
                    "has_images": False
                }
            }
        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Could not decode {file_path} with any known encoding")


def read_markdown(file_path):
    """Read markdown file, separate frontmatter and body."""
    try:
        import yaml
    except ImportError:
        yaml = None
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    frontmatter = {}
    body = content
    
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if match and yaml:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            body = match.group(2)
        except:
            pass
    
    return {
        "type": "markdown",
        "frontmatter": frontmatter,
        "body": body,
        "metadata": {
            "file": os.path.basename(file_path),
            "has_frontmatter": bool(frontmatter),
            "has_images": "![" in body or "<img" in body
        }
    }


def read_html(file_path):
    """Read HTML and extract main content."""
    try:
        import trafilatura
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
        
        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_images=True,
            output_format="markdown"
        )
        
        return {
            "type": "html",
            "content": result or "",
            "metadata": {
                "file": os.path.basename(file_path),
                "has_images": True
            }
        }
    except ImportError:
        # Fallback: BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            main = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
            text = main.get_text("\n\n") if main else soup.get_text("\n\n")
            return {
                "type": "html",
                "content": text,
                "metadata": {"file": os.path.basename(file_path), "has_images": False}
            }
        except ImportError:
            raise ImportError("Install trafilatura or beautifulsoup4 to read HTML")


def read_image(file_path):
    """Return image metadata for vision transcription."""
    from PIL import Image
    
    img = Image.open(file_path)
    return {
        "type": "image",
        "metadata": {
            "file": os.path.basename(file_path),
            "format": img.format,
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "needs_vision_transcription": True
        }
    }


def read_audio(file_path):
    """Return audio metadata for Whisper transcription."""
    return {
        "type": "audio",
        "metadata": {
            "file": os.path.basename(file_path),
            "needs_transcription": True,
            "suggested_model": "base"  # Whisper model size
        }
    }


def read_file(file_path):
    """Main entry point: detect format and read file."""
    fmt = detect_format(file_path)
    
    readers = {
        "pdf": read_pdf,
        "docx": read_docx,
        "txt": read_txt,
        "markdown": read_markdown,
        "html": read_html,
        "image": read_image,
        "audio": read_audio,
    }
    
    reader = readers.get(fmt)
    if reader:
        result = reader(file_path)
        result["detected_format"] = fmt
        result["file_path"] = file_path
        return result
    else:
        return {
            "detected_format": "unknown",
            "file_path": file_path,
            "error": f"Unsupported file format: {fmt}"
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read raw source file for wiki ingestion")
    parser.add_argument("file_path", help="Path to source file")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    args = parser.parse_args()
    
    result = read_file(args.file_path)
    
    json_output = json.dumps(result, indent=2, ensure_ascii=False)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
    else:
        print(json_output)
