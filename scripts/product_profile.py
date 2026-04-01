#!/usr/bin/env python3
"""
product_profile — Extract text from product documents (PDF/TXT/MD).
Agent does the AI analysis to understand the product.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from _common import base_argparser, handle_schema, fail

SCHEMA = {
    "name": "product_profile",
    "description": "Extract text from product documents. Agent analyzes to understand product.",
    "input": {"type": "object", "properties": {"file": {"type": "string"}}},
    "output": {"type": "object", "properties": {"text": {"type": "string"}}},
}


def extract_text(file_path: str) -> str:
    """Extract text from PDF/TXT/MD file."""
    p = Path(file_path)
    if not p.exists():
        fail(f"文件不存在: {file_path}")

    suffix = p.suffix.lower()

    # TXT/MD: direct read
    if suffix in (".txt", ".md", ".markdown"):
        return p.read_text(encoding="utf-8")

    # PDF: use pypdf
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
            if text:
                return text
            fail("PDF 无文本内容。可能是扫描件，请改用文字说明或先 OCR。")
        except ImportError:
            fail("需要安装 pypdf: pip install pypdf")

    # Fallback
    return p.read_text(encoding="utf-8", errors="ignore")


def main():
    parser = base_argparser("Extract text from product document")
    parser.add_argument("--file", "-f", required=True, help="PDF/TXT/MD file path")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    text = extract_text(args.file)

    # Truncate to 50k chars (enough for product info)
    if len(text) > 50000:
        text = text[:50000] + "\n\n[已截断]"
        print(f"[product_profile] 截断至 50000 字符", file=sys.stderr)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"[product_profile] 写入: {args.output}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
