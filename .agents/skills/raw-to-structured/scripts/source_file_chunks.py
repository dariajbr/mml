#!/usr/bin/env python3
"""Inspect and split large source documents without changing the originals."""

import argparse
import json
import os
import re
from pathlib import Path


_FORMATS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
}


def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        return _FORMATS[suffix]
    except KeyError as exc:
        label = suffix or "without a suffix"
        raise ValueError(
            f"Unsupported or atomic source format {label}; "
            "expected PDF, DOCX, TXT, Markdown, or HTML"
        ) from exc


def inspect_file(path: str) -> dict:
    """Return byte size and lightweight metadata without returning source text."""
    stat_result = os.stat(path)
    source = Path(path).resolve()
    source_format = _detect_format(source)
    info = {
        "file_path": str(source),
        "format": source_format,
        "size_bytes": stat_result.st_size,
    }

    if source_format == "pdf":
        import fitz

        document = fitz.open(str(source))
        try:
            info["page_count"] = len(document)
        finally:
            document.close()
    elif source_format == "docx":
        from docx import Document

        document = Document(str(source))
        info["paragraph_count"] = len(document.paragraphs)
        info["table_count"] = len(document.tables)

    return info


def _is_markdown_table(text: str) -> bool:
    lines = text.splitlines()
    if len(lines) < 2 or lines[0].startswith(("    ", "\t")):
        return False
    if "|" not in lines[0] or "|" not in lines[1]:
        return False

    def cells(line: str) -> list[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [cell.strip() for cell in line.split("|")]

    headers = cells(lines[0])
    delimiters = cells(lines[1])
    return len(headers) == len(delimiters) and all(
        re.fullmatch(r":?-{3,}:?", delimiter) for delimiter in delimiters
    )


def _paragraph_units(text: str) -> list[dict]:
    spans = []
    start = 0
    for match in re.finditer(r"\r?\n[ \t]*\r?\n(?:[ \t]*\r?\n)*", text):
        spans.append((text[start:match.start()], match.group()))
        start = match.end()
    spans.append((text[start:], ""))

    units = []
    for paragraph_number, (raw, separator) in enumerate(spans, 1):
        if not raw and not separator:
            continue
        label = f"paragraph {paragraph_number}"
        is_heading = bool(re.match(r"^ {0,3}#{1,6}[ \t]+\S", raw))
        is_table = _is_markdown_table(raw)
        if is_table and units and units[-1]["kind"] == "heading":
            heading = units.pop()
            table_prefix = "".join(raw.splitlines(keepends=True)[:2])
            units.append({
                "text": heading["text"] + raw + separator,
                "first_unit": heading["first_unit"],
                "last_unit": label,
                "kind": "table",
                "split_prefix": heading["text"] + table_prefix,
                "split_body": raw[len(table_prefix):] + separator,
            })
            continue
        unit = {
            "text": raw + separator,
            "first_unit": label,
            "last_unit": label,
            "kind": "heading" if is_heading else "table" if is_table else "paragraph",
        }
        if is_table:
            table_prefix = "".join(raw.splitlines(keepends=True)[:2])
            unit["split_prefix"] = table_prefix
            unit["split_body"] = raw[len(table_prefix):] + separator
        units.append(unit)
    return units


def _table_to_markdown(table) -> str:
    rows = []
    for row in table.rows:
        cells = [
            cell.text.replace("|", r"\|").replace("\n", "<br>")
            for cell in row.cells
        ]
        rows.append(cells)
    if not rows or not rows[0]:
        return ""
    width = len(rows[0])
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _docx_units(path: Path) -> list[dict]:
    from docx import Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(str(path))
    units = []
    paragraph_number = 0
    heading_number = 0
    table_number = 0

    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            paragraph = Paragraph(child, document)
            text = paragraph.text
            if not text.strip():
                continue
            style_name = paragraph.style.name if paragraph.style is not None else ""
            heading_match = re.match(r"Heading\s+([1-6])$", style_name)
            if heading_match:
                heading_number += 1
                label = f"heading {heading_number}"
                kind = "heading"
                text = "#" * int(heading_match.group(1)) + " " + text
            else:
                paragraph_number += 1
                label = f"paragraph {paragraph_number}"
                kind = "paragraph"
            units.append({
                "text": text,
                "first_unit": label,
                "last_unit": label,
                "kind": kind,
            })
        elif isinstance(child, CT_Tbl):
            table_number += 1
            markdown = _table_to_markdown(Table(child, document))
            if not markdown:
                continue
            label = f"table {table_number}"
            table_lines = markdown.splitlines()
            table_prefix = "\n".join(table_lines[:2]) + "\n"
            table_body = markdown[len(table_prefix):]
            if units and units[-1]["kind"] == "heading":
                heading = units.pop()
                units.append({
                    "text": heading["text"] + "\n\n" + markdown,
                    "first_unit": heading["first_unit"],
                    "last_unit": label,
                    "kind": "table",
                    "split_prefix": heading["text"] + "\n\n" + table_prefix,
                    "split_body": table_body,
                })
            else:
                units.append({
                    "text": markdown,
                    "first_unit": label,
                    "last_unit": label,
                    "kind": "table",
                    "split_prefix": table_prefix,
                    "split_body": table_body,
                })

    return units


def _html_table_to_markdown(table) -> str:
    rows = []
    for html_row in table.find_all("tr"):
        cells = html_row.find_all(["th", "td"], recursive=False)
        if cells:
            rows.append([
                cell.get_text(" ", strip=True).replace("|", r"\|")
                for cell in cells
            ])
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _html_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    try:
        import trafilatura
    except ImportError:
        trafilatura = None
    if trafilatura is not None:
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_links=True,
            output_format="markdown",
        )
        if extracted:
            return extracted

    try:
        from bs4 import BeautifulSoup, NavigableString
    except ImportError as exc:
        raise ImportError("Install trafilatura or beautifulsoup4 to split HTML") from exc
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    for table in soup.find_all("table"):
        markdown = _html_table_to_markdown(table)
        table.replace_with(NavigableString("\n\n" + markdown + "\n\n"))

    roots = soup.find_all(["main", "article"])
    if roots:
        root_ids = {id(root) for root in roots}
        roots = [
            root for root in roots
            if not any(id(parent) in root_ids for parent in root.parents)
        ]
    else:
        roots = [soup.body or soup]
    return "\n\n".join(root.get_text("\n\n") for root in roots)


def _extract_units(path: Path, source_format: str) -> list[dict]:
    if source_format == "pdf":
        import fitz

        document = fitz.open(str(path))
        try:
            units = []
            for page_number, page in enumerate(document, 1):
                text = page.get_text()
                if text.strip():
                    label = f"page {page_number}"
                    units.append({
                        "text": text,
                        "first_unit": label,
                        "last_unit": label,
                        "kind": "page",
                    })
            return units
        finally:
            document.close()
    if source_format == "docx":
        return _docx_units(path)
    if source_format in ("txt", "markdown"):
        with path.open("r", encoding="utf-8", newline="") as handle:
            return _paragraph_units(handle.read())
    if source_format == "html":
        return _paragraph_units(_html_text(path))
    raise ValueError(f"Unsupported source format: {source_format}")


def _chunk_text(source: Path, first_unit: str, last_unit: str, body: str) -> str:
    safe_source = str(source).replace("--", "- -")
    header = (
        f"<!-- Original source: {safe_source}; "
        f"unit range: {first_unit} to {last_unit} -->"
    )
    return header + "\n\n" + body + "\n"


def _split_unit(unit: dict, source: Path, max_chars: int) -> list[dict]:
    prefix = unit.get("split_prefix", "")
    remaining = unit.get("split_body", unit["text"])
    fragments = []
    while True:
        body = prefix + remaining
        if len(_chunk_text(source, unit["first_unit"], unit["last_unit"], body)) <= max_chars:
            fragments.append({**unit, "text": body})
            return fragments
        available = max_chars - len(
            _chunk_text(source, unit["first_unit"], unit["last_unit"], prefix)
        )
        if available < 1:
            raise ValueError("max_chars is too small for the chunk source metadata")
        newline = remaining.rfind("\n", 0, available)
        cut = newline + 1 if newline >= 0 else available
        fragments.append({**unit, "text": prefix + remaining[:cut]})
        remaining = remaining[cut:]
        if not remaining:
            return fragments


def _pack_units(units: list[dict], source: Path, max_chars: int) -> list[dict]:
    packed = []
    current = []

    def flush() -> None:
        if current:
            packed.append({
                "text": "".join(unit["text"] for unit in current),
                "first_unit": current[0]["first_unit"],
                "last_unit": current[-1]["last_unit"],
            })

    for unit in units:
        candidate = current + [unit]
        body = "".join(item["text"] for item in candidate)
        if len(_chunk_text(
            source, candidate[0]["first_unit"], candidate[-1]["last_unit"], body
        )) <= max_chars:
            current = candidate
            continue
        flush()
        current = []
        if len(_chunk_text(
            source, unit["first_unit"], unit["last_unit"], unit["text"]
        )) <= max_chars:
            current = [unit]
        else:
            packed.extend(_split_unit(unit, source, max_chars))
    flush()
    return packed


def _validated_output_dir(output_dir: str) -> Path:
    output = Path(output_dir).resolve()
    repository = Path(__file__).resolve().parents[4]
    allowed_root = (repository / ".tmp" / "llm-wiki").resolve()
    try:
        relative = output.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError(
            f"Output directory must be under {allowed_root}: {output}"
        ) from exc
    if relative == Path("."):
        raise ValueError(
            f"Output directory must name a source-specific subdirectory of {allowed_root}"
        )
    return output


def split_file(path: str, output_dir: str, max_chars: int, reason: str) -> dict:
    """Write numbered Markdown chunks and manifest.json; never modify path."""
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1000:
        raise ValueError("max_chars must be an integer of at least 1000")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")

    info = inspect_file(path)
    source = Path(info["file_path"])
    if not source.is_file():
        raise ValueError(f"Source is not a regular file: {source}")
    output = _validated_output_dir(output_dir)
    if output.exists() and not output.is_dir():
        raise ValueError(f"Output path is not a directory: {output}")
    manifest_path = output / "manifest.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite existing manifest: {manifest_path}")

    units = _extract_units(source, info["format"])
    packed = _pack_units(units, source, max_chars)
    chunks = []
    contents = []
    for number, chunk in enumerate(packed, 1):
        chunk_path = output / f"chunk-{number:03d}.md"
        content = _chunk_text(
            source, chunk["first_unit"], chunk["last_unit"], chunk["text"]
        )
        if chunk_path.exists() or chunk_path.is_symlink():
            raise FileExistsError(f"Refusing to overwrite existing chunk: {chunk_path}")
        chunks.append({
            "path": str(chunk_path),
            "first_unit": chunk["first_unit"],
            "last_unit": chunk["last_unit"],
            "char_count": len(content),
        })
        contents.append((chunk_path, content))

    manifest = {
        "version": 1,
        "source": str(source),
        "format": info["format"],
        "size_bytes": info["size_bytes"],
        "reason": reason,
        "max_chars": max_chars,
        "chunks": chunks,
    }
    missing_dirs = []
    cursor = output
    while not cursor.exists():
        missing_dirs.append(cursor)
        cursor = cursor.parent
    created_files = []
    try:
        output.mkdir(parents=True, exist_ok=True)
        for chunk_path, content in contents:
            with chunk_path.open("x", encoding="utf-8", newline="\n") as handle:
                created_files.append(chunk_path)
                handle.write(content)
        with manifest_path.open("x", encoding="utf-8", newline="\n") as handle:
            created_files.append(manifest_path)
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except BaseException:
        for created_file in reversed(created_files):
            try:
                created_file.unlink()
            except FileNotFoundError:
                pass
        for directory in reversed(missing_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect or split a large source without modifying the original"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="show lightweight source metadata")
    inspect_parser.add_argument("path", help="source file path")

    split_parser = subparsers.add_parser("split", help="write Markdown chunks and a manifest")
    split_parser.add_argument("path", help="source file path")
    split_parser.add_argument("--output-dir", required=True, help="directory outside the vault")
    split_parser.add_argument("--max-chars", required=True, type=int, help="maximum chunk size")
    split_parser.add_argument("--reason", required=True, help="reason for splitting")

    args = parser.parse_args()
    if args.command == "inspect":
        result = inspect_file(args.path)
    else:
        result = split_file(args.path, args.output_dir, args.max_chars, args.reason)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
