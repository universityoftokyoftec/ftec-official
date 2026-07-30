#!/usr/bin/env python3
"""Fetch the F-tec note RSS feed and write assets/note-latest.json."""

from __future__ import annotations

import argparse
import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

RSS_URL = "https://note.com/utokyo_ftec/rss"
DEFAULT_OUTPUT = Path("assets/note-latest.json")
JST = ZoneInfo("Asia/Tokyo")
ALLOWED_HOSTS = {"note.com", "www.note.com"}

TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Post:
    title: str
    url: str
    published: datetime
    excerpt: str
    image: str


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def first_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = {name.lower() for name in names}
    for child in list(element):
        if local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""


def parse_datetime(value: str) -> datetime:
    value = value.strip()
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    parsed = email.utils.parsedate_to_datetime(value)
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def strip_html(value: str, limit: int = 150) -> str:
    text = TAG_RE.sub(" ", value or "")
    text = html.unescape(text)
    text = SPACE_RE.sub(" ", text).strip()
    for suffix in ("続きをみる", "続きを読む"):
        text = text.replace(suffix, "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def extract_image(item: ET.Element, html_sources: Iterable[str]) -> str:
    for child in item.iter():
        name = local_name(child.tag)
        if name in {"thumbnail", "content", "enclosure"}:
            url = (child.attrib.get("url") or "").strip()
            media_type = (child.attrib.get("type") or "").lower()
            if url and (name != "enclosure" or media_type.startswith("image/")):
                return url

    for source in html_sources:
        match = IMG_RE.search(source or "")
        if match:
            return html.unescape(match.group(1))
    return ""


def validate_note_url(value: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        return ""
    if not parsed.path.startswith("/utokyo_ftec/"):
        return ""
    return value


def parse_feed(xml_bytes: bytes) -> list[Post]:
    root = ET.fromstring(xml_bytes)
    items = [element for element in root.iter() if local_name(element.tag) in {"item", "entry"}]
    posts: list[Post] = []

    for item in items:
        title = first_text(item, {"title"})
        url = first_text(item, {"link"})
        if not url:
            for child in list(item):
                if local_name(child.tag) == "link":
                    url = (child.attrib.get("href") or "").strip()
                    if url:
                        break
        url = validate_note_url(url)
        if not title or not url:
            continue

        date_value = first_text(item, {"pubdate", "published", "updated", "date"})
        try:
            published = parse_datetime(date_value)
        except (TypeError, ValueError, OverflowError):
            published = datetime.min.replace(tzinfo=timezone.utc)

        description = first_text(item, {"description", "summary"})
        content = first_text(item, {"encoded", "content"})
        excerpt = strip_html(description or content)
        image = extract_image(item, (content, description))

        posts.append(Post(title=title, url=url, published=published, excerpt=excerpt, image=image))

    posts.sort(key=lambda post: post.published, reverse=True)
    return posts


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "F-tec-Website-RSS-Updater/1.0 (+https://note.com/utokyo_ftec)",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"RSS request failed: HTTP {response.status}")
        return response.read()


def serialize(posts: list[Post]) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    serialized_posts = []
    for post in posts[:3]:
        local = post.published.astimezone(JST)
        serialized_posts.append(
            {
                "title": post.title,
                "url": post.url,
                "date_iso": local.date().isoformat(),
                "date_display": local.strftime("%Y.%m.%d"),
                "excerpt": post.excerpt,
                "image": post.image,
            }
        )
    return {
        "source": RSS_URL,
        "updated_at": now.isoformat(timespec="seconds"),
        "posts": serialized_posts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Use a local RSS/XML file instead of downloading")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        xml_bytes = args.input.read_bytes() if args.input else fetch_feed(RSS_URL)
        posts = parse_feed(xml_bytes)
        if not posts:
            raise RuntimeError("No valid F-tec note posts were found in the RSS feed")

        payload = serialize(posts)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        args.output.write_text(text, encoding="utf-8")
        print(f"Updated {args.output} with {len(payload['posts'])} post(s).")
        return 0
    except Exception as exc:  # noqa: BLE001 - workflow must fail loudly
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
