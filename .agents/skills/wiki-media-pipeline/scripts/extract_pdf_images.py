#!/usr/bin/env python3
"""
Extract all embedded images from a PDF file.

Usage:
    python extract_pdf_images.py <pdf_path> <output_dir> [--prefix <slug>]

Output: JSON list of extracted image metadata to stdout.
"""

import argparse
import json
import os
import fitz  # PyMuPDF


def extract_pdf_images(pdf_path, output_dir, prefix=None):
    """Extract embedded images from PDF. Returns list of metadata dicts."""
    os.makedirs(output_dir, exist_ok=True)
    
    source_slug = prefix or os.path.splitext(os.path.basename(pdf_path))[0]
    doc = fitz.open(pdf_path)
    extracted = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        
        for img_idx, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            
            ext = base_image["ext"]
            filename = f"{source_slug}-page{page_num+1}-fig{img_idx+1}.{ext}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(base_image["image"])
            
            extracted.append({
                "path": filepath,
                "filename": filename,
                "page": page_num + 1,
                "index": img_idx + 1,
                "width": base_image["width"],
                "height": base_image["height"],
                "ext": ext,
                "source": pdf_path
            })
    
    doc.close()
    return extracted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract images from PDF")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("output_dir", help="Directory to save extracted images")
    parser.add_argument("--prefix", default=None, help="Filename prefix for extracted images")
    args = parser.parse_args()
    
    result = extract_pdf_images(args.pdf_path, args.output_dir, args.prefix)
    print(json.dumps(result, indent=2))
