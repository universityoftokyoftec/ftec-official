#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
from pathlib import Path

VERSION = "20260802-15"
STYLE_ID = "ftec-hotfix-inline"
SCRIPT_ID = "ftec-hotfix-inline-script"


def inject(path: Path, css: str, js: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    original = text

    # Remove all prior linked or inline hotfixes so versions never stack.
    text = re.sub(r'<link[^>]+data-ftec-patch="css"[^>]*>', '', text, flags=re.I)
    text = re.sub(r'<script[^>]+data-ftec-patch="js"[^>]*></script>', '', text, flags=re.I)
    text = re.sub(rf'<style[^>]+id=["\']{STYLE_ID}["\'][^>]*>.*?</style>', '', text, flags=re.I | re.S)
    text = re.sub(rf'<script[^>]+id=["\']{SCRIPT_ID}["\'][^>]*>.*?</script>', '', text, flags=re.I | re.S)

    style = f'<style id="{STYLE_ID}" data-version="{VERSION}">\n{css}\n</style>'
    script = f'<script id="{SCRIPT_ID}" data-version="{VERSION}">\n{js}\n</script>'

    if '</head>' in text:
        text = text.replace('</head>', style + '\n</head>', 1)
    else:
        text = style + '\n' + text

    if '</body>' in text:
        text = text.replace('</body>', script + '\n</body>', 1)
    else:
        text += '\n' + script

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    source = Path(__file__).resolve().parent
    if not site.is_dir():
        raise SystemExit(f"Site directory not found: {site}")
    css = (source / 'ftec-hotfix.css').read_text(encoding='utf-8')
    js = (source / 'ftec-hotfix.js').read_text(encoding='utf-8')
    html_files = sorted(site.rglob('*.html'))
    changed = sum(inject(p, css, js) for p in html_files)
    (site / '.nojekyll').touch()
    print(f"F-tec inline hotfix v15: {changed}/{len(html_files)} HTML files updated.")
    if not html_files or changed == 0:
        raise SystemExit('No HTML files were patched.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
