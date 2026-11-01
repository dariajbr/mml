#!/usr/bin/env python3
"""
Batch process media from multiple source documents for wiki ingestion.

Orchestrates extraction, optimization, and organization into the wiki media structure.

Usage:
    python3 process_media_batch.py <config_json>

Config JSON format (see references/media-schema.md):
    {
      "wiki_root": "/path/to/wiki",
      "temp_root": "/path/to/temporary/media-staging",
      "sources": [
        {
          "path": "/path/to/sources/planning-guide.pdf",
          "type": "pdf",
          "slug": "planning-guide",
          "extract_mode": "embedded",
          "pages": null
        },
        {
          "path": "/path/to/sources/whiteboard.jpg",
          "type": "image",
          "slug": "whiteboard-study-group-notes",
          "image_type": "whiteboard"
        }
      ]
    }

Output: JSON report of all processed media to stdout.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def run_extractor(script_name, *args):
    """Run an extraction script and return parsed JSON output."""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script_path] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Extractor {script_name} failed: {result.stderr}")
    return json.loads(result.stdout)


def resolve_staging_dir(temp_root, slug):
    resolved_temp_root = os.path.realpath(temp_root)
    staging_path = os.path.join(resolved_temp_root, slug)
    staging_dir = os.path.realpath(staging_path)
    if os.path.dirname(staging_dir) != resolved_temp_root:
        raise ValueError(f"Staging directory escapes temp_root: {slug}")
    return staging_path, staging_dir


def is_path_within(path, directory):
    return os.path.commonpath([path, directory]) == directory


def paths_overlap(first, second):
    return is_path_within(first, second) or is_path_within(second, first)


def validate_staging_location(wiki_root, temp_root, staging_dir, media_dir):
    resolved_wiki_root = os.path.realpath(wiki_root)
    resolved_temp_root = os.path.realpath(temp_root)
    resolved_media_dir = os.path.realpath(media_dir)
    if paths_overlap(staging_dir, resolved_media_dir):
        raise ValueError(
            f"Staging directory overlaps media output directory: {staging_dir}"
        )
    if is_path_within(resolved_temp_root, resolved_wiki_root):
        raise ValueError(f"temp_root must be outside wiki_root: {temp_root}")


def process_source(source, wiki_root, temp_root):
    """Process a single source file. Returns list of processed media records."""
    source_path = source["path"]
    slug = source["slug"]
    source_type = source["type"]

    staging_path, staging_dir = resolve_staging_dir(temp_root, slug)
    media_dir = os.path.join(wiki_root, "media", "extracted", slug)
    validate_staging_location(wiki_root, temp_root, staging_dir, media_dir)
    if os.path.lexists(staging_path) or os.path.lexists(staging_dir):
        raise FileExistsError(f"Staging directory already exists: {staging_path}")

    staging_created = False
    try:
        os.makedirs(staging_dir, exist_ok=False)
        staging_created = True
        os.makedirs(media_dir, exist_ok=True)
        records = []

        # Step 1: Extract based on source type
        if source_type == "pdf":
            extract_mode = source.get("extract_mode", "embedded")
            pages = source.get("pages")

            if extract_mode == "embedded":
                extracted = run_extractor(
                    "extract_pdf_images.py", source_path, staging_dir, "--prefix", slug
                )
            elif extract_mode == "render":
                pages_arg = ",".join(map(str, pages)) if pages else None
                args = [source_path, staging_dir, "--prefix", slug, "--dpi", "200"]
                if pages_arg:
                    args.extend(["--pages", pages_arg])
                extracted = run_extractor("render_pdf_page.py", *args)
            else:
                raise ValueError(f"Unknown extract_mode: {extract_mode}")

        elif source_type == "docx":
            extracted = run_extractor(
                "extract_docx_images.py", source_path, staging_dir, "--prefix", slug
            )

        elif source_type == "image":
            # Direct copy for image files
            ext = os.path.splitext(source_path)[1]
            filename = f"{slug}{ext}"
            dest = os.path.join(staging_dir, filename)
            shutil.copy2(source_path, dest)
            extracted = [{
                "path": dest,
                "filename": filename,
                "source": source_path
            }]

        else:
            raise ValueError(f"Unknown source type: {source_type}")

        # Step 2: Optimize each extracted file
        for item in extracted:
            item_path = item["path"]

            # Determine image type hint from source config or filename
            image_type = source.get("image_type", "default")

            # Build optimized output path
            base_name = os.path.splitext(item["filename"])[0]
            # Clean up the filename: remove slug prefix if present to avoid doubling
            if base_name.startswith(f"{slug}-"):
                base_name = base_name[len(f"{slug}-"):]

            # Determine format from type
            type_formats = {
                "diagram": "png", "chart": "png", "table": "png", "map": "png",
                "photo": "jpg", "whiteboard": "jpg", "screenshot": "png", "formula": "png"
            }
            out_ext = type_formats.get(image_type, "png")
            optimized_name = f"{base_name}.{out_ext}"
            optimized_path = os.path.join(media_dir, optimized_name)

            # Run optimizer
            optimizer_args = [item_path, optimized_path]
            if image_type != "default":
                optimizer_args.extend(["--type", image_type])
            opt_result = run_extractor("optimize_image.py", *optimizer_args)

            records.append({
                "source": source_path,
                "slug": slug,
                "source_type": source_type,
                "image_type": image_type,
                "original": item_path,
                "optimized": opt_result["output_path"],
                "wiki_path": f"media/extracted/{slug}/{optimized_name}",
                "width": opt_result["width"],
                "height": opt_result["height"],
                "bytes": opt_result["optimized_bytes"],
                "compression_ratio": opt_result.get("compression_ratio", 1)
            })

        return records
    finally:
        if staging_created:
            shutil.rmtree(staging_dir)


def main(config_path):
    with open(config_path) as f:
        config = json.load(f)
    
    sources = config["sources"]
    wiki_root = os.path.abspath(config["wiki_root"])
    temp_root = os.path.abspath(config.get(
        "temp_root",
        os.path.join(os.path.dirname(wiki_root), ".tmp", "llm-wiki", "media-staging")
    ))

    staging_targets = set()
    staging_paths = []
    for source in sources:
        slug = source["slug"]
        if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug):
            raise ValueError("Each source slug must match ^[a-z0-9][a-z0-9-]*$")
        staging_path, staging_dir = resolve_staging_dir(temp_root, slug)
        media_dir = os.path.join(wiki_root, "media", "extracted", slug)
        validate_staging_location(wiki_root, temp_root, staging_dir, media_dir)
        if staging_dir in staging_targets:
            raise ValueError(f"Duplicate staging directory: {staging_dir}")
        staging_targets.add(staging_dir)
        staging_paths.append((staging_path, staging_dir))

    for staging_path, staging_dir in staging_paths:
        if os.path.lexists(staging_path) or os.path.lexists(staging_dir):
            raise FileExistsError(f"Staging directory already exists: {staging_path}")

    os.makedirs(temp_root, exist_ok=True)
    all_records = []
    
    for source in sources:
        try:
            records = process_source(source, wiki_root, temp_root)
            all_records.extend(records)
        except Exception as e:
            all_records.append({
                "source": source["path"],
                "slug": source["slug"],
                "error": str(e)
            })
    
    report = {
        "wiki_root": wiki_root,
        "total_processed": len([r for r in all_records if "error" not in r]),
        "total_errors": len([r for r in all_records if "error" in r]),
        "media": all_records
    }
    
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process wiki media")
    parser.add_argument("config", help="Path to batch config JSON file")
    args = parser.parse_args()
    main(args.config)
