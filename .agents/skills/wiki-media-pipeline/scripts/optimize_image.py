#!/usr/bin/env python3
"""
Optimize extracted images for local Markdown readers in a wiki.

Resizes to max-width, compresses, and converts to appropriate format.
Handles diagrams (PNG), photos (JPEG), and mixed content.

Usage:
    python3 optimize_image.py <input_path> <output_path> [options]

Options:
    --max-width N       Max width in pixels (default: auto-detect by type)
    --quality N         JPEG quality 1-100 (default: 85)
    --format FMT        Force output format: png, jpg (default: auto)
    --type TYPE         Image type hint: diagram, chart, photo, table, map, whiteboard

Output: JSON metadata to stdout.
"""

import argparse
import json
import os
from PIL import Image


# Default parameters by image type
TYPE_DEFAULTS = {
    "diagram":    {"max_width": 1200, "format": "png", "quality": None},
    "chart":      {"max_width": 1200, "format": "png", "quality": None},
    "table":      {"max_width": 1600, "format": "png", "quality": None},
    "map":        {"max_width": 1600, "format": "png", "quality": None},
    "photo":      {"max_width": 1600, "format": "jpg", "quality": 85},
    "whiteboard": {"max_width": 1600, "format": "jpg", "quality": 85},
    "screenshot": {"max_width": 1200, "format": "png", "quality": None},
    "formula":    {"max_width": 1200, "format": "png", "quality": None},
    "default":    {"max_width": 1200, "format": None, "quality": 85},
}


def optimize_image(input_path, output_path, max_width=None, quality=None, 
                   format_hint=None, type_hint=None):
    """Resize and compress an image for local Markdown readers."""
    
    # Apply type defaults
    defaults = TYPE_DEFAULTS.get(type_hint, TYPE_DEFAULTS["default"])
    max_width = max_width or defaults["max_width"]
    quality = quality or defaults["quality"]
    out_format = format_hint or defaults["format"]
    
    img = Image.open(input_path)
    original_size = os.path.getsize(input_path)
    
    # Convert mode for target format compatibility
    target_format = out_format or os.path.splitext(output_path)[1][1:].lower()
    if target_format in ("jpg", "jpeg") and img.mode in ("RGBA", "P", "LA"):
        # Create white background for transparency
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode in ("RGBA", "LA"):
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
    elif img.mode not in ("RGB", "L") and target_format == "png":
        img = img.convert("RGBA") if img.mode == "P" else img
    
    # Resize if width exceeds max
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    
    # Determine output format
    if out_format:
        ext = out_format
        output_path = os.path.splitext(output_path)[0] + f".{ext}"
    else:
        ext = os.path.splitext(output_path)[1][1:].lower() or "png"
    
    # Save with appropriate parameters
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if ext in ("jpg", "jpeg"):
        save_kwargs = {"quality": quality, "optimize": True}
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "JPEG", **save_kwargs)
    elif ext == "png":
        img.save(output_path, "PNG", optimize=True)
    else:
        img.save(output_path)
    
    optimized_size = os.path.getsize(output_path)
    
    return {
        "input_path": input_path,
        "output_path": output_path,
        "format": ext,
        "width": img.width,
        "height": img.height,
        "original_bytes": original_size,
        "optimized_bytes": optimized_size,
        "compression_ratio": round(original_size / optimized_size, 2) if optimized_size > 0 else 0
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize image for local Markdown readers")
    parser.add_argument("input_path", help="Input image path")
    parser.add_argument("output_path", help="Output image path")
    parser.add_argument("--max-width", type=int, default=None)
    parser.add_argument("--quality", type=int, default=None)
    parser.add_argument("--format", default=None, choices=["png", "jpg", "jpeg"])
    parser.add_argument("--type", default=None, 
                        choices=["diagram", "chart", "table", "map", "photo", 
                                "whiteboard", "screenshot", "formula"])
    args = parser.parse_args()
    
    result = optimize_image(
        args.input_path, args.output_path,
        max_width=args.max_width,
        quality=args.quality,
        format_hint=args.format,
        type_hint=args.type
    )
    print(json.dumps(result, indent=2))
