#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

VERSION = "20260802-7"

# Emojiになり得る矢印に「テキスト表示指定 U+FE0E」を付ける。
# HTML本文だけでなく、埋め込みCSSの content:"↗" なども一括で直せる。
EMOJI_PRONE_ARROW_RE = re.compile(
    r"([\u2196\u2197\u2198\u2199\u2934\u2935\u2B05\u2B06\u2B07\u27A1])[\uFE0E\uFE0F]?"
)


def relative_asset(html_path: Path, site_root: Path, filename: str) -> str:
    target = site_root / "ftec_hotfix" / filename
    return os.path.relpath(target, start=html_path.parent).replace(os.sep, "/")


def inject(path: Path, site_root: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    original = text

    # iPhoneで↗が青い絵文字になる問題を、全ページ・全疑似要素を含めて修正。
    text = EMOJI_PRONE_ARROW_RE.sub(lambda m: m.group(1) + "\uFE0E", text)

    css = relative_asset(path, site_root, "ftec-hotfix.css")
    js = relative_asset(path, site_root, "ftec-hotfix.js")
    css_tag = f'<link rel="stylesheet" href="{css}?v={VERSION}" data-ftec-patch="css">'
    js_tag = f'<script src="{js}?v={VERSION}" defer data-ftec-patch="js"></script>'

    text = re.sub(r'<link[^>]+data-ftec-patch="css"[^>]*>', css_tag, text)
    text = re.sub(r'<script[^>]+data-ftec-patch="js"[^>]*></script>', js_tag, text)

    if 'data-ftec-patch="css"' not in text:
        text = text.replace('</head>', css_tag + '</head>', 1) if '</head>' in text else css_tag + '\n' + text
    if 'data-ftec-patch="js"' not in text:
        text = text.replace('</body>', js_tag + '</body>', 1) if '</body>' in text else text + '\n' + js_tag

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not root.is_dir():
        raise SystemExit(f"Site directory not found: {root}")

    files = sorted(root.rglob("*.html"))
    changed = sum(inject(path, root) for path in files)
    print(f"F-tec hotfix v7: {changed}/{len(files)} HTML files updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
