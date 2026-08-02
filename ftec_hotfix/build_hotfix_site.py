#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

VERSION = "20260802-8"

EXTERNAL_SVG = (
    '<svg class="ftec-hotfix-inline-arrow-v8 is-external" viewBox="0 0 18 18" '
    'aria-hidden="true" focusable="false"><path d="M4 14L14 4M7 4H14V11"/></svg>'
)
INTERNAL_SVG = (
    '<svg class="ftec-hotfix-inline-arrow-v8 is-internal" viewBox="0 0 24 14" '
    'aria-hidden="true" focusable="false"><path d="M1 7H22M17 2L22 7L17 12"/></svg>'
)

# 「矢印だけが入ったspan/i/b等」を、配信前にSVGへ変換する。
# これによりJS実行前でもiPhoneの絵文字矢印が一瞬表示されない。
ARROW_ELEMENT_RE = re.compile(
    r'<(?P<tag>span|i|b|em|strong|small)(?P<attrs>[^>]*)>'
    r'\s*(?P<arrow>[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴])[\uFE0E\uFE0F]?\s*'
    r'</(?P=tag)>',
    flags=re.IGNORECASE,
)

ARROW_ONLY_CONTAINER_RE = re.compile(
    r'<(?P<tag>a|button)(?P<attrs>[^>]*)>'
    r'\s*(?P<arrow>[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴])[\uFE0E\uFE0F]?\s*'
    r'</(?P=tag)>',
    flags=re.IGNORECASE,
)


def relative_asset(html_path: Path, site_root: Path, filename: str) -> str:
    target = site_root / "ftec_hotfix" / filename
    return os.path.relpath(target, start=html_path.parent).replace(os.sep, "/")


def replace_arrow_element(match: re.Match[str]) -> str:
    tag = match.group("tag")
    attrs = match.group("attrs")
    arrow = match.group("arrow")
    svg = EXTERNAL_SVG if arrow in {"↗", "⤴"} else INTERNAL_SVG
    return f'<{tag}{attrs}>{svg}</{tag}>'


def inject(path: Path, site_root: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    original = text

    text = ARROW_ELEMENT_RE.sub(replace_arrow_element, text)
    text = ARROW_ONLY_CONTAINER_RE.sub(replace_arrow_element, text)

    css = relative_asset(path, site_root, "ftec-hotfix.css")
    js = relative_asset(path, site_root, "ftec-hotfix.js")
    css_tag = f'<link rel="stylesheet" href="{css}?v={VERSION}" data-ftec-patch="css">'
    js_tag = f'<script src="{js}?v={VERSION}" defer data-ftec-patch="js"></script>'

    # 旧版タグがあれば必ずv8へ更新する。
    text = re.sub(r'<link[^>]+data-ftec-patch="css"[^>]*>', css_tag, text)
    text = re.sub(r'<script[^>]+data-ftec-patch="js"[^>]*></script>', js_tag, text)

    if 'data-ftec-patch="css"' not in text:
        text = text.replace("</head>", css_tag + "</head>", 1) if "</head>" in text else css_tag + "\n" + text
    if 'data-ftec-patch="js"' not in text:
        text = text.replace("</body>", js_tag + "</body>", 1) if "</body>" in text else text + "\n" + js_tag

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
    print(f"F-tec hotfix v8: {changed}/{len(files)} HTML files updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
