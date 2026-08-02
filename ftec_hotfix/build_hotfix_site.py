#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

VERSION = "20260802-5"
CSS_TAG = f'<link rel="stylesheet" href="/ftec_hotfix/ftec-hotfix.css?v={VERSION}" data-ftec-patch="css">'
JS_TAG = f'<script src="/ftec_hotfix/ftec-hotfix.js?v={VERSION}" defer data-ftec-patch="js"></script>'


def inject(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    original = text

    # 過去のパッチタグが元HTMLに残っていても、必ずv5へ置換
    import re
    text = re.sub(r'<link[^>]+data-ftec-patch="css"[^>]*>', CSS_TAG, text)
    text = re.sub(r'<script[^>]+data-ftec-patch="js"[^>]*></script>', JS_TAG, text)

    if 'data-ftec-patch="css"' not in text:
        text = text.replace('</head>', CSS_TAG + '</head>', 1) if '</head>' in text else CSS_TAG + '\n' + text
    if 'data-ftec-patch="js"' not in text:
        text = text.replace('</body>', JS_TAG + '</body>', 1) if '</body>' in text else text + '\n' + JS_TAG

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '_site').resolve()
    if not root.is_dir():
        raise SystemExit(f'Site directory not found: {root}')
    files = sorted(root.rglob('*.html'))
    changed = sum(inject(path) for path in files)
    print(f'F-tec hotfix v5: {changed}/{len(files)} HTML files updated.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
