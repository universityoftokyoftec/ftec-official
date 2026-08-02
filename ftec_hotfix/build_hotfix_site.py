#!/usr/bin/env python3
from __future__ import annotations
import html
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

VERSION = "20260802-16"
STYLE_ID = "ftec-hotfix-inline"
SCRIPT_ID = "ftec-hotfix-inline-script"
ARROW_CHARS = "←→↗➡➜➝➞⟶⟹⇢⇥›»＞﹥⤴➤➥➦➧➨➩➪➫➬➭➮➯➱⮕"
ARROW_RE = re.compile(f"[{re.escape(ARROW_CHARS)}\\ufe0e\\ufe0f]")
ARROW_ONLY_NODE_RE = re.compile(
    rf'<(?P<tag>span|i|b|em|strong|small)(?P<attrs>[^>]*)>\s*[{re.escape(ARROW_CHARS)}\ufe0e\ufe0f]+\s*</(?P=tag)>',
    re.I | re.S,
)
ANCHOR_RE = re.compile(r'(?P<open><a\b(?P<attrs>[^>]*)>)(?P<body>.*?)(?P<close></a>)', re.I | re.S)
BUTTON_RE = re.compile(r'(?P<open><button\b(?P<attrs>[^>]*)>)(?P<body>.*?)(?P<close></button>)', re.I | re.S)
EXTERNAL_HOSTS = {
    'note.com', 'x.com', 'twitter.com', 'instagram.com', 'facebook.com',
    'line.me', 'lin.ee', 'youtube.com', 'youtu.be'
}


def svg(kind: str) -> str:
    if kind == 'external':
        path = '<path d="M4 14L14 4M7 4h7v7"/>'
        view = '0 0 18 18'
    elif kind == 'left':
        path = '<path d="M23 7H2M7 2L2 7l5 5"/>'
        view = '0 0 24 14'
    else:
        path = '<path d="M1 7h21M17 2l5 5-5 5"/>'
        view = '0 0 24 14'
    return (
        f'<span class="ftec-arrow-slot" aria-hidden="true" data-ftec-arrow-kind="{kind}">'
        f'<svg class="ftec-arrow-svg" viewBox="{view}" aria-hidden="true" focusable="false">{path}</svg>'
        '</span>'
    )


def attr_value(attrs: str, name: str) -> str:
    match = re.search(rf'\b{re.escape(name)}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', attrs, re.I)
    if not match:
        return ''
    return next((group for group in match.groups() if group is not None), '')


def add_data_attrs(open_tag: str, **values: str) -> str:
    result = open_tag
    for name, value in values.items():
        attr = name.replace('_', '-')
        if re.search(rf'\b{re.escape(attr)}\s*=', result, re.I):
            result = re.sub(
                rf'\b{re.escape(attr)}\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)',
                f'{attr}="{html.escape(value, quote=True)}"', result, count=1, flags=re.I,
            )
        else:
            result = result[:-1] + f' {attr}="{html.escape(value, quote=True)}">'
    return result


def external_href(href: str) -> bool:
    if not href or href.startswith(('#', 'mailto:', 'tel:', '/', './', '../')):
        return False
    parsed = urlparse(href)
    if not parsed.scheme or not parsed.netloc:
        return False
    hostname = (parsed.hostname or '').lower()
    return any(hostname == host or hostname.endswith('.' + host) for host in EXTERNAL_HOSTS) or hostname != 'universityoftokyoftec.github.io'


def plain_text(fragment: str) -> str:
    return html.unescape(re.sub(r'<[^>]+>', '', fragment))


def normalize_anchor(match: re.Match[str]) -> str:
    open_tag, attrs, body, close_tag = match.group('open', 'attrs', 'body', 'close')
    if not ARROW_RE.search(body):
        return match.group(0)
    href = attr_value(attrs, 'href')
    kind = 'external' if external_href(href) else ('left' if '←' in body else 'right')
    only_arrow = not ARROW_RE.sub('', plain_text(body)).strip()

    body, replacements = ARROW_ONLY_NODE_RE.subn(lambda _: svg(kind), body)
    body = ARROW_RE.sub('', body)
    if replacements == 0 or 'ftec-arrow-slot' not in body:
        body += svg(kind)

    data = {
        'data_ftec_arrow_ready': 'true',
        'data_ftec_arrow_kind': kind,
    }
    if kind == 'external':
        data['data_ftec_external'] = 'true'
    if only_arrow:
        data['data_ftec_arrow_only'] = 'true'
    open_tag = add_data_attrs(open_tag, **data)
    return open_tag + body + close_tag


def normalize_button(match: re.Match[str]) -> str:
    open_tag, body, close_tag = match.group('open', 'body', 'close')
    if not ARROW_RE.search(body):
        return match.group(0)
    visible = plain_text(body).strip()
    kind = 'left' if '←' in body else 'right'
    only_arrow = not ARROW_RE.sub('', visible).strip()
    body, replacements = ARROW_ONLY_NODE_RE.subn(lambda _: svg(kind), body)
    body = ARROW_RE.sub('', body)
    if replacements == 0 or 'ftec-arrow-slot' not in body:
        body += svg(kind)
    data = {
        'data_ftec_arrow_ready': 'true',
        'data_ftec_arrow_kind': kind,
    }
    if only_arrow:
        data['data_ftec_arrow_only'] = 'true'
    open_tag = add_data_attrs(open_tag, **data)
    return open_tag + body + close_tag


def normalize_static_arrows(text: str) -> str:
    text = ANCHOR_RE.sub(normalize_anchor, text)
    text = BUTTON_RE.sub(normalize_button, text)
    return text


def inject(path: Path, css: str, js: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    original = text

    text = re.sub(r'<link[^>]+data-ftec-patch="css"[^>]*>', '', text, flags=re.I)
    text = re.sub(r'<script[^>]+data-ftec-patch="js"[^>]*></script>', '', text, flags=re.I)
    text = re.sub(rf'<style[^>]+id=["\']{STYLE_ID}["\'][^>]*>.*?</style>', '', text, flags=re.I | re.S)
    text = re.sub(rf'<script[^>]+id=["\']{SCRIPT_ID}["\'][^>]*>.*?</script>', '', text, flags=re.I | re.S)

    # Replace source arrow characters before the page reaches Safari.
    text = normalize_static_arrows(text)

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
    print(f"F-tec inline hotfix v16: {changed}/{len(html_files)} HTML files updated.")
    if not html_files or changed == 0:
        raise SystemExit('No HTML files were patched.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
