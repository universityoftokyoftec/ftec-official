#!/usr/bin/env python3
"""Update F-tec's latest note posts and cache their header images locally.

The note RSS gives us article metadata and usually a media:thumbnail URL. Instead
of hot-linking that URL from the website, this script downloads the image during
the GitHub Actions run and stores it under assets/note-images/. The website then
loads the local copy, avoiding referrer/hot-linking failures in browsers.
"""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import mimetypes
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

RSS_URL = "https://note.com/utokyo_ftec/rss"
DEFAULT_OUTPUT = Path("assets/note-latest.json")
DEFAULT_IMAGE_DIR = Path("assets/note-images")
FALLBACK_WEB_PATH = "../assets/note-fallback.svg"
JST = ZoneInfo("Asia/Tokyo")
ARTICLE_HOSTS = {"note.com", "www.note.com"}
MAX_POSTS = 3
MAX_IMAGE_BYTES = 12 * 1024 * 1024

TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")

CONTENT_TYPE_EXTENSIONS = {
    "image/avif": ".avif",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class Post:
    title: str
    url: str
    published: datetime
    excerpt: str
    source_image: str
    local_image: str = ""


class OgImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.image = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.image or tag.lower() != "meta":
            return
        values = {key.lower(): (value or "") for key, value in attrs}
        key = (values.get("property") or values.get("name") or "").lower()
        if key in {"og:image", "og:image:url", "twitter:image"}:
            self.image = values.get("content", "").strip()


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


def normalize_https_url(value: str) -> str:
    value = html.unescape((value or "").strip())
    if value.startswith("//"):
        value = "https:" + value
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return ""
    return value


def extract_image(item: ET.Element, html_sources: Iterable[str]) -> str:
    # media:thumbnail / media:content / enclosure. ElementTree keeps the
    # namespace in {…} but local_name() intentionally strips it.
    for child in item.iter():
        name = local_name(child.tag)
        if name in {"thumbnail", "content", "enclosure"}:
            url = normalize_https_url(child.attrib.get("url") or "")
            media_type = (child.attrib.get("type") or "").lower()
            if url and (name != "enclosure" or not media_type or media_type.startswith("image/")):
                return url

    for source in html_sources:
        match = IMG_RE.search(source or "")
        if match:
            return normalize_https_url(match.group(1))
    return ""


def validate_note_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ARTICLE_HOSTS:
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
        source_image = extract_image(item, (content, description))

        posts.append(
            Post(
                title=title,
                url=url,
                published=published,
                excerpt=excerpt,
                source_image=source_image,
            )
        )

    posts.sort(key=lambda post: post.published, reverse=True)
    return posts


def request_bytes(url: str, *, referer: str = "https://note.com/") -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; F-tec-Website-Updater/2.0; +https://note.com/utokyo_ftec)",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"HTTP {status}")
        content_type = response.headers.get_content_type().lower()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_IMAGE_BYTES:
            raise RuntimeError("image is too large")
        data = response.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            raise RuntimeError("image is too large")
        return data, content_type


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "F-tec-Website-RSS-Updater/2.0 (+https://note.com/utokyo_ftec)",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"RSS request failed: HTTP {response.status}")
        return response.read()


def fetch_article_og_image(article_url: str) -> str:
    request = urllib.request.Request(
        article_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; F-tec-Website-Updater/2.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            return ""
        raw = response.read(3 * 1024 * 1024)
        charset = response.headers.get_content_charset() or "utf-8"
    parser = OgImageParser()
    parser.feed(raw.decode(charset, errors="replace"))
    return normalize_https_url(parser.image)


def article_id(article_url: str) -> str:
    last = urlparse(article_url).path.rstrip("/").rsplit("/", 1)[-1]
    cleaned = SAFE_ID_RE.sub("-", last).strip("-")
    if cleaned:
        return cleaned[:80]
    return hashlib.sha256(article_url.encode("utf-8")).hexdigest()[:20]


def extension_for(content_type: str, image_url: str) -> str:
    content_type = content_type.split(";", 1)[0].strip().lower()
    if content_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[content_type]
    guessed = mimetypes.guess_extension(content_type) if content_type.startswith("image/") else None
    if guessed:
        return ".jpg" if guessed == ".jpe" else guessed
    path_ext = Path(urlparse(image_url).path).suffix.lower()
    if path_ext in {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}:
        return ".jpg" if path_ext == ".jpeg" else path_ext
    raise RuntimeError(f"unsupported image content type: {content_type or 'unknown'}")


def write_if_changed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def load_previous_images(output: Path) -> dict[str, str]:
    try:
        payload = json.loads(output.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    result: dict[str, str] = {}
    for item in payload.get("posts", []):
        if isinstance(item, dict) and isinstance(item.get("url"), str) and isinstance(item.get("image"), str):
            result[item["url"]] = item["image"]
    return result


def previous_local_file(web_path: str, image_dir: Path) -> Path | None:
    if not web_path.startswith("../assets/note-images/"):
        return None
    filename = web_path.rsplit("/", 1)[-1]
    candidate = image_dir / filename
    return candidate if candidate.is_file() else None


def cache_post_image(post: Post, image_dir: Path, previous: dict[str, str]) -> Post:
    candidates: list[str] = []
    if post.source_image:
        candidates.append(post.source_image)
    try:
        og_image = fetch_article_og_image(post.url)
        if og_image and og_image not in candidates:
            candidates.append(og_image)
    except Exception as exc:  # article fallback is best-effort
        print(f"WARNING: could not inspect article OGP for {post.url}: {exc}", file=sys.stderr)

    for image_url in candidates:
        try:
            data, content_type = request_bytes(image_url, referer=post.url)
            if not content_type.startswith("image/"):
                raise RuntimeError(f"not an image ({content_type})")
            ext = extension_for(content_type, image_url)
            filename = f"{article_id(post.url)}{ext}"
            destination = image_dir / filename
            write_if_changed(destination, data)
            return replace(
                post,
                source_image=image_url,
                local_image=f"../assets/note-images/{filename}",
            )
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
            print(f"WARNING: image download failed for {image_url}: {exc}", file=sys.stderr)

    # Keep the last known local image if note or its CDN is temporarily unavailable.
    old = previous_local_file(previous.get(post.url, ""), image_dir)
    if old:
        return replace(post, local_image=f"../assets/note-images/{old.name}")

    return replace(post, local_image=FALLBACK_WEB_PATH)


def cleanup_stale_images(image_dir: Path, active_web_paths: set[str]) -> None:
    active_names = {path.rsplit("/", 1)[-1] for path in active_web_paths if "/note-images/" in path}
    if not image_dir.exists():
        return
    for path in image_dir.iterdir():
        if path.is_file() and path.name not in active_names and path.name != ".gitkeep":
            path.unlink()


def serialize(posts: list[Post]) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    serialized_posts = []
    for post in posts[:MAX_POSTS]:
        local = post.published.astimezone(JST)
        serialized_posts.append(
            {
                "title": post.title,
                "url": post.url,
                "date_iso": local.date().isoformat(),
                "date_display": local.strftime("%Y.%m.%d"),
                "excerpt": post.excerpt,
                "image": post.local_image or FALLBACK_WEB_PATH,
                "source_image": post.source_image,
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
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    args = parser.parse_args()

    try:
        xml_bytes = args.input.read_bytes() if args.input else fetch_feed(RSS_URL)
        posts = parse_feed(xml_bytes)[:MAX_POSTS]
        if not posts:
            raise RuntimeError("No valid F-tec note posts were found in the RSS feed")

        previous = load_previous_images(args.output)
        cached = [cache_post_image(post, args.image_dir, previous) for post in posts]
        payload = serialize(cached)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        args.output.write_text(text, encoding="utf-8")

        active = {post.local_image for post in cached}
        cleanup_stale_images(args.image_dir, active)
        print(f"Updated {args.output} with {len(cached)} post(s) and local images.")
        return 0
    except Exception as exc:  # workflow must fail loudly
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
