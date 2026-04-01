#!/usr/bin/env python3
"""
product_profile — Extract text from product documents (PDF/MD/TXT/DOCX).

Skill mode: Use --extract-only to extract text, Agent does the AI analysis.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from _common import (
    base_argparser, handle_schema, fail, SKILL_ROOT
)

SCHEMA = {
    "name": "product_profile",
    "description": "Extract text from product documents (PDF/MD/TXT/DOCX). Agent does the AI analysis.",
    "input": {
        "type": "object",
        "properties": {
            "file": {
                "type": "string",
                "description": "Path to product document (PDF/MD/TXT/DOCX)"
            }
        },
        "required": ["file"]
    },
    "output": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Extracted text content"}
        }
    },
    "examples": {
        "extract_pdf": "python scripts/product_profile.py --file intro.pdf --extract-only -o output/product-raw.txt",
        "extract_docx": "python scripts/product_profile.py --file product.docx --extract-only -o output/product-raw.txt"
    },
    "errors": {
        "no_input": "未提供文件路径 → 用 --file",
        "file_not_found": "文件不存在 → 检查路径",
        "pdf_parse_failed": "PDF 解析失败 → pip install pypdf",
        "docx_parse_failed": "DOCX 解析失败 → pip install python-docx"
    }
}


def _pdf_to_text(p: Path) -> str:
    """Extract text from PDF: pypdf first, then PyMuPDF (fitz) if installed."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except ImportError:
        pass
    except Exception:
        pass
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(p))
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
    except ImportError:
        pass
    except Exception:
        pass
    return ""


def read_product_file(file_path: str) -> str:
    """Read product document from file."""
    p = Path(file_path)
    if not p.exists():
        fail(f"File not found: {file_path}")

    suffix = p.suffix.lower()

    if suffix in (".txt", ".md", ".markdown"):
        return p.read_text(encoding="utf-8")

    if suffix == ".pdf":
        text = _pdf_to_text(p)
        text = text.strip()
        if text:
            return text
        fail(
            "PDF 未解析出文本。可能原因：\n"
            "1. 扫描件/图片版 PDF — 请先 OCR 或改用文字说明\n"
            "2. 未安装 pypdf — 运行: pip install pypdf\n"
            "3. 加密 PDF — 请先解密"
        )

    if suffix == ".docx":
        try:
            from docx import Document
            doc = Document(str(p))
            return "\n".join(par.text for par in doc.paragraphs if par.text.strip())
        except ImportError:
            fail("读取 .docx 需要: pip install python-docx")
        except Exception as e:
            fail(f"DOCX 解析失败: {e}")

    return p.read_text(encoding="utf-8", errors="ignore")


def main():
    parser = base_argparser("Extract text from product documents")
    parser.add_argument("--file", "-f", help="Path to product document (PDF/MD/TXT/DOCX)")
    parser.add_argument("--extract-only", action="store_true", help="Extract text only (default behavior)")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    if not args.file:
        fail("请提供文件路径: --file <路径>")

    print(f"[product_profile] Extracting text from: {args.file}", file=sys.stderr)
    product_text = read_product_file(args.file)

    if len(product_text) > 100000:
        product_text = product_text[:100000] + "\n\n[...truncated...]"
        print(f"[product_profile] Truncated to 100000 chars", file=sys.stderr)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(product_text, encoding="utf-8")
        print(f"[product_profile] Wrote: {args.output}", file=sys.stderr)
    else:
        print(product_text)


if __name__ == "__main__":
    main()
