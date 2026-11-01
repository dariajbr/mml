#!/usr/bin/env python3
"""
Render PDF pages as high-resolution images.

Use this when the layout matters: composite diagrams, formatted tables,
text+figure combinations that lose meaning when extracted separately.

Usage:
    python render_pdf_page.py <pdf_path> <output_dir> [--pages 1,3,5] [--dpi 200] [--prefix <slug>]

Output: JSON list of rendered page metadata to stdout.
"""

import argparse
import json
import os
from pdf2image import convert_from_path


def render_pdf_pages(pdf_path, output_dir, pages=None, dpi=200, prefix=None):
    """Render PDF pages as images. Returns list of metadata dicts."""
    os.makedirs(output_dir, exist_ok=True)
    
    source_slug = prefix or os.path.splitext(os.path.basename(pdf_path))[0]
    kwargs = {"dpi": dpi}
    
    if pages:
        kwargs["first_page"] = min(pages)
        kwargs["last_page"] = max(pages)
    
    images = convert_from_path(pdf_path, **kwargs)
    
    # Map images to requested page numbers
    all_pages = pages or list(range(1, len(images) + 1))
    
    extracted = []
    for i, image in enumerate(images):
        page_num = all_pages[i]
        filename = f"{source_slug}-page{page_num}-render.png"
        filepath = os.path.join(output_dir, filename)
        image.save(filepath, "PNG")
        extracted.append({
            "path": filepath,
            "filename": filename,
            "page": page_num,
            "dpi": dpi,
            "width": image.width,
            "height": image.height,
            "source": pdf_path
        })
    
    return extracted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render PDF pages as images")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("output_dir", help="Directory to save rendered images")
    parser.add_argument("--pages", default=None, help="Comma-separated page numbers (e.g., 1,3,5)")
    parser.add_argument("--dpi", type=int, default=200, help="Rendering resolution DPI (default: 200)")
    parser.add_argument("--prefix", default=None, help="Filename prefix")
    args = parser.parse_args()
    
    pages = [int(p.strip()) for p in args.pages.split(",")] if args.pages else None
    result = render_pdf_pages(args.pdf_path, args.output_dir, pages, args.dpi, args.prefix)
    print(json.dumps(result, indent=2))
