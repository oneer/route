"""Build a chapter/article Markdown version for the Dahua Imaging anthology.

This script uses the PDF table of contents pages to split the anthology into:

    chapter -> article -> text and images

Unlike the raw page export, page numbers are only used as anchors and are not
the document's primary structure.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


CHINESE_NUMERAL = "一二三四五六七八九十"


@dataclass(frozen=True)
class TocEntry:
    chapter: str
    index: int
    title: str
    logical_page: int


def clean_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\.{3,}", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def clean_page_text(text: str, logical_page: int | None = None) -> str:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if logical_page is not None and line == str(logical_page):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def compact_heading(text: str) -> str:
    return re.sub(r"[\s：:，,。.\-—_（）()]+", "", text).lower()


def split_article_metadata(entry: TocEntry, first_page_text: str) -> tuple[list[str], str]:
    """Remove duplicated chapter/title lines and return metadata plus body text."""
    metadata: list[str] = []
    body: list[str] = []
    title_compact = compact_heading(f"{entry.index}.{entry.title}")
    plain_title_compact = compact_heading(entry.title)
    chapter_compact = compact_heading(entry.chapter)
    skipping_prefix = True

    for line in first_page_text.split("\n"):
        line_clean = line.strip()
        if not line_clean:
            continue

        compact = compact_heading(line_clean)
        is_chapter_line = compact == chapter_compact
        is_title_line = compact == title_compact or compact == plain_title_compact
        is_title_fragment = compact and (compact in title_compact or compact in plain_title_compact)
        if skipping_prefix and (is_chapter_line or is_title_line):
            continue

        if line_clean.startswith("作者："):
            metadata.append(f"- {line_clean}")
            continue
        if re.match(r"^\d{4}年\d{1,2}月\d{1,2}日$", line_clean):
            metadata.append(f"- 日期：{line_clean}")
            continue

        if skipping_prefix and is_title_fragment:
            continue

        skipping_prefix = False
        body.append(line_clean)

    return metadata, "\n".join(body).strip()


def parse_toc(pdf_path: Path, toc_page_start: int = 4, toc_page_end: int = 9) -> list[TocEntry]:
    entries: list[TocEntry] = []
    current_chapter = ""
    chapter_re = re.compile(rf"^(第[{CHINESE_NUMERAL}]+章\s+.+?|附录：.+?)(?:\s+\d+)?$")
    entry_re = re.compile(r"^(\d+)\.\s*(.+?)\s+(\d+)$")

    with pdfplumber.open(pdf_path) as pdf:
        for page_number in range(toc_page_start, toc_page_end + 1):
            text = pdf.pages[page_number - 1].extract_text() or ""
            for raw_line in text.split("\n"):
                line = clean_line(raw_line)
                if not line or line.isdigit() or line == "目录":
                    continue

                chapter_match = chapter_re.match(line)
                if chapter_match:
                    chapter = chapter_match.group(1)
                    chapter = re.sub(r"\s+\d+$", "", chapter).strip()
                    current_chapter = chapter
                    continue

                entry_match = entry_re.match(line)
                if entry_match and current_chapter:
                    entries.append(
                        TocEntry(
                            chapter=current_chapter,
                            index=int(entry_match.group(1)),
                            title=entry_match.group(2).strip(),
                            logical_page=int(entry_match.group(3)),
                        )
                    )

    return entries


def image_refs_for_physical_page(figures_dir: Path, physical_page: int) -> list[Path]:
    return sorted(figures_dir.glob(f"page_{physical_page:04d}_img_*.png"))


def article_slug(entry: TocEntry) -> str:
    title = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", entry.title, flags=re.UNICODE).strip("_")
    return f"{entry.index:02d}_{title[:80]}"


def refine(
    pdf_path: Path,
    figures_dir: Path,
    out_path: Path,
    page_offset: int = 9,
    toc_page_start: int = 4,
    toc_page_end: int = 9,
) -> Path:
    entries = parse_toc(pdf_path, toc_page_start=toc_page_start, toc_page_end=toc_page_end)
    if not entries:
        raise RuntimeError("No TOC entries parsed from PDF.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        f"# {pdf_path.stem}",
        "",
        f"> 来源 PDF：`{pdf_path.name}`",
        ">",
        "> 整理方式：按原 PDF 目录拆分为“章节 → 文章”。图片按原始所在页插入到对应文章中；页码只作为溯源信息，不再作为主结构。",
        ">",
        "> 说明：这是自动章节精修版，已去掉大多数页脚页码；复杂表格、公式、跨页图片说明仍建议人工复核。",
        "",
        "## 目录",
        "",
    ]

    last_chapter = ""
    for entry in entries:
        if entry.chapter != last_chapter:
            lines.append(f"- {entry.chapter}")
            last_chapter = entry.chapter
        lines.append(f"  - [{entry.index}. {entry.title}](#{article_slug(entry).lower()})")

    lines.extend(["", "## 正文", ""])

    with pdfplumber.open(pdf_path) as pdf:
        last_chapter = ""
        for i, entry in enumerate(entries):
            next_entry = entries[i + 1] if i + 1 < len(entries) else None
            start_physical = entry.logical_page + page_offset
            end_physical = (next_entry.logical_page + page_offset - 1) if next_entry else len(pdf.pages)
            end_physical = min(end_physical, len(pdf.pages))

            if entry.chapter != last_chapter:
                lines.extend([f"## {entry.chapter}", ""])
                last_chapter = entry.chapter

            lines.extend(
                [
                    f"### {entry.index}. {entry.title}",
                    "",
                    f"<a id=\"{article_slug(entry).lower()}\"></a>",
                    "",
                    f"> 原 PDF 逻辑页：{entry.logical_page}；物理页范围：{start_physical}-{end_physical}",
                    "",
                ]
            )

            for physical_page in range(start_physical, end_physical + 1):
                page = pdf.pages[physical_page - 1]
                logical_page = physical_page - page_offset
                text = clean_page_text(page.extract_text() or "", logical_page=logical_page)
                if physical_page == start_physical and text:
                    metadata, text = split_article_metadata(entry, text)
                    if metadata:
                        lines.extend(["**文章信息**", "", *metadata, ""])
                if text:
                    lines.extend([text, ""])

                image_paths = image_refs_for_physical_page(figures_dir, physical_page)
                if image_paths:
                    lines.extend(["**配图**", ""])
                    for image_path in image_paths:
                        rel = image_path.relative_to(out_path.parent).as_posix()
                        lines.extend([f"![{entry.title} - 原 PDF 第 {physical_page} 页图片]({rel})", ""])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine Dahua PDF export into chapter/article Markdown.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--figures-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--page-offset", type=int, default=9)
    args = parser.parse_args()

    out_path = refine(args.pdf, args.figures_dir, args.out, page_offset=args.page_offset)
    print(out_path)


if __name__ == "__main__":
    main()
