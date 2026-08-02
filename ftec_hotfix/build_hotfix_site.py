#!/usr/bin/env python3
"""Inject the lightweight F-tec patch files into the generated Pages artifact.

The source HTML files in the repository are not modified. Only the temporary
_site directory created by GitHub Actions is changed before deployment.
"""

from __future__ import annotations

import sys
from pathlib import Path

CSS_TAG = '<link rel="stylesheet" href="/ftec_hotfix/ftec-hotfix.css?v=20260802" data-ftec-patch="css">'
JS_TAG = '<script src="/ftec_hotfix/ftec-hotfix.js?v=20260802" defer data-ftec-patch="js"></script>'


def inject(html_path: Path) -> bool:
    text = html_path.read_text(encoding="utf-8", errors="strict")
    original = text

    if 'data-ftec-patch="css"' not in text:
        if "</head>" in text:
            text = text.replace("</head>", f"{CSS_TAG}</head>", 1)
        else:
            text = f"{CSS_TAG}\n{text}"

    if 'data-ftec-patch="js"' not in text:
        if "</body>" in text:
            text = text.replace("</body>", f"{JS_TAG}</body>", 1)
        else:
            text = f"{text}\n{JS_TAG}\n"

    if text != original:
        html_path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not root.is_dir():
        raise SystemExit(f"Site directory not found: {root}")

    html_files = sorted(root.rglob("*.html"))
    changed = sum(inject(path) for path in html_files)
    print(f"Injected F-tec patch into {changed}/{len(html_files)} HTML files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
