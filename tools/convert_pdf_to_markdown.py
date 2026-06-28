"""Convert a PDF into a page-anchored Markdown document.

The converter is intentionally conservative:
- text stays attached to its original page;
- image crops are exported into a figures directory;
- the Markdown references each image under the page where it appears.

It is meant for learning notes and review material, not for perfect layout
reconstruction.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pdfplumber


def safe_stem(path: Path) -> str:
    text = path.stem
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", text, flags=re.UNICODE)
    return text.strip("_") or "pdf_export"


def clean_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    cleaned: list[str] = []
    blank = False
    for line in lines:
        line = line.strip()
        if not line:
            if not blank:
                cleaned.append("")
            blank = True
            continue
        cleaned.append(line)
        blank = False
    return "\n".join(cleaned).strip()


def export_page_images(page, figures_dir: Path, page_number: int, resolution: int, min_width: float, min_height: float) -> list[str]:
    image_paths: list[str] = []
    for image_index, image in enumerate(page.images, start=1):
        width = float(image.get("width") or 0.0)
        height = float(image.get("height") or 0.0)
        if width < min_width or height < min_height:
            continue

        bbox = (image["x0"], image["top"], image["x1"], image["bottom"])
        out_path = figures_dir / f"page_{page_number:04d}_img_{image_index:02d}.png"
        try:
            page.crop(bbox).to_image(resolution=resolution).save(out_path)
        except Exception as exc:  # pragma: no cover - depends on PDF object quirks
            print(f"[warn] failed to export page {page_number} image {image_index}: {exc}")
            continue
        image_paths.append(out_path.name)
    return image_paths


def convert(pdf_path: Path, out_dir: Path, resolution: int, min_width: float, min_height: float) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{safe_stem(pdf_path)}.md"

    lines: list[str] = [
        f"# {pdf_path.stem}",
        "",
        f"> 来源 PDF：`{pdf_path.name}`",
        ">",
        "> 转换说明：本文档按 PDF 页码整理。每页先放可提取文本，再放该页导出的图片。",
        "> 图片为页面中图片区域的裁剪结果；复杂排版、表格、公式和扫描页仍建议人工复核。",
        "",
        "## 文档信息",
        "",
    ]

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        total_images = sum(len(page.images) for page in pdf.pages)
        lines.extend(
            [
                f"- 页数：{total_pages}",
                f"- PDF 图片对象数：{total_images}",
                f"- 图片目录：`figures/`",
                "",
                "## 正文",
                "",
            ]
        )

        for page_number, page in enumerate(pdf.pages, start=1):
            if page_number == 1 or page_number % 25 == 0:
                print(f"[info] processing page {page_number}/{total_pages}")

            text = clean_text(page.extract_text() or "")
            image_names = export_page_images(
                page,
                figures_dir,
                page_number,
                resolution=resolution,
                min_width=min_width,
                min_height=min_height,
            )

            lines.extend([f"## 第 {page_number} 页", ""])
            if text:
                lines.extend([text, ""])
            else:
                lines.extend(["_本页未提取到可复制文本。_", ""])

            if image_names:
                lines.extend(["### 本页图片", ""])
                for image_name in image_names:
                    lines.extend([f"![第 {page_number} 页图片](figures/{image_name})", ""])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a PDF into page-anchored Markdown with extracted images.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--resolution", type=int, default=120)
    parser.add_argument("--min-width", type=float, default=24.0)
    parser.add_argument("--min-height", type=float, default=24.0)
    args = parser.parse_args()

    pdf_path = args.pdf
    out_dir = args.out_dir or Path("pdf_exports") / safe_stem(pdf_path)
    md_path = convert(pdf_path, out_dir, args.resolution, args.min_width, args.min_height)
    print(md_path)


if __name__ == "__main__":
    main()
