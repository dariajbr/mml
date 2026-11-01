#!/usr/bin/env python3
"""
Extract all images from a Word (.docx) document.

Usage:
    python extract_docx_images.py <docx_path> <output_dir> [--prefix <slug>]

Output: JSON list of extracted image metadata to stdout.
"""

import argparse
import json
import os
from docx import Document


def extract_docx_images(docx_path, output_dir, prefix=None):
    """Extract images from DOCX. Returns list of metadata dicts."""
    os.makedirs(output_dir, exist_ok=True)
    
    source_slug = prefix or os.path.splitext(os.path.basename(docx_path))[0]
    doc = Document(docx_path)
    
    # Collect all image parts from relationships
    image_parts = []
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_parts.append(rel.target_part)
    
    extracted = []
    for idx, image_part in enumerate(image_parts):
        # Determine extension from content type
        content_type = image_part.content_type
        ext_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/gif": "gif",
            "image/bmp": "bmp",
            "image/tiff": "tiff"
        }
        ext = ext_map.get(content_type, "bin")
        
        filename = f"{source_slug}-image{idx+1}.{ext}"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_part.blob)
        
        extracted.append({
            "path": filepath,
            "filename": filename,
            "index": idx + 1,
            "content_type": content_type,
            "ext": ext,
            "size_bytes": len(image_part.blob),
            "source": docx_path
        })
    
    return extracted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract images from DOCX")
    parser.add_argument("docx_path", help="Path to DOCX file")
    parser.add_argument("output_dir", help="Directory to save extracted images")
    parser.add_argument("--prefix", default=None, help="Filename prefix")
    args = parser.parse_args()
    
    result = extract_docx_images(args.docx_path, args.output_dir, args.prefix)
    print(json.dumps(result, indent=2))
