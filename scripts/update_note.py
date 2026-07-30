#!/usr/bin/env python3
"""Update F-tec's latest note cards and cache article header images.

Primary source:
  note's public-facing creator contents endpoint
  https://note.com/api/v2/creators/utokyo_ftec/contents?kind=note&page=1

Fallback source:
  note RSS

The list endpoint exposes the article's `eyecatch` URL directly, which is more
reliable than trying to infer the image from RSS or scrape each article page.

If a local image download fails:
1. keep the previous local copy when available;
2. otherwise use note's external eyecatch URL;
3. only then use the fallback SVG.

This avoids replacing every image with the blue fallback card.
"""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import mimetypes
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

NOTE_USER = "utokyo_ftec"
API_URL = (
    f"https://note.com/api/v2/creators/{NOTE_USER}/contents"
    "?kind=note&page=1"
)
RSS_URL = f"https://note.com/{NOTE_USER}/rss"

DEFAULT_OUTPUT = Path("assets/note-latest.json")
DEFAULT_IMAGE_DIR = Path("assets/note-images")
FALLBACK_WEB_PATH = "../assets/note-fallback.svg"

JST = ZoneInfo("Asia/Tokyo")
MAX_POSTS = 3
MAX_IMAGE_BYTES = 15 * 1024 * 1024

TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")

IMAGE_EXTENSIONS = {
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


def browser_headers(*, accept: str, referer: str = "https://note.com/") -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36"
        ),
        "Accept": accept,
        "Accept-Language": "ja,en-US;q=0.8,en;q=0.6",
        "Referer": referer,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def request_bytes(
    url: str,
    *,
    accept: str,
    referer: str = "https://note.com/",
    max_bytes: int = MAX_IMAGE_BYTES,
    retries: int = 3,
) -> tuple[bytes, str]:
    last_error: Exception | None = None

    for attempt in range(retries):
        headers = browser_headers(accept=accept, referer=referer)
        if attempt == 1:
            # Some CDNs dislike a cross-page Referer.
            headers.pop("Referer", None)
        elif attempt >= 2:
            headers["User-Agent"] = "Mozilla/5.0"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise RuntimeError(f"HTTP {status}")

                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes:
                    raise RuntimeError("response is too large")

                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise RuntimeError("response is too large")

                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                return data, content_type
        except (OSError, RuntimeError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.2 * (attempt + 1))

    raise RuntimeError(str(last_error or "request failed"))


def fetch_json(url: str) -> dict:
    data, content_type = request_bytes(
        url,
        accept="application/json,text/plain,*/*",
        max_bytes=6 * 1024 * 1024,
    )
    if content_type and "json" not in content_type and not data.lstrip().startswith(b"{"):
        raise RuntimeError(f"note API did not return JSON ({content_type})")
    payload = json.loads(data.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("note API returned an unexpected payload")
    return payload


def normalize_https_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = html.unescape(value.strip())
    if value.startswith("//"):
        value = "https:" + value
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return ""
    return value


def parse_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        return datetime.min.replace(tzinfo=timezone.utc)

    raw = value.strip()
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass

    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def strip_html(value: object, limit: int = 150) -> str:
    if not isinstance(value, str):
        return ""
    text = TAG_RE.sub(" ", value)
    text = html.unescape(text)
    text = SPACE_RE.sub(" ", text).strip()
    for suffix in ("続きをみる", "続きを読む"):
        text = text.replace(suffix, "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def first_value(item: dict, names: Iterable[str]) -> object:
    for name in names:
        value = item.get(name)
        if value not in (None, ""):
            return value
    return ""


def parse_api_posts(payload: dict) -> list[Post]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("note API response has no data object")

    contents = data.get("contents")
    if not isinstance(contents, list):
        raise RuntimeError("note API response has no contents list")

    posts: list[Post] = []
    for item in contents:
        if not isinstance(item, dict):
            continue

        status = str(item.get("status") or "").lower()
        if status and status not in {"published", "publish"}:
            continue

        title = str(first_value(item, ("name", "title")) or "").strip()
        key = str(first_value(item, ("key", "noteKey", "note_key")) or "").strip()

        url = normalize_https_url(
            first_value(item, ("noteUrl", "note_url", "url"))
        )
        if not url and key:
            url = f"https://note.com/{NOTE_USER}/n/{key}"

        if not title or not url:
            continue

        published = parse_datetime(
            first_value(item, ("publishAt", "publish_at", "publishedAt", "published_at"))
        )
        excerpt = strip_html(
            first_value(item, ("description", "body", "excerpt"))
        )

        image = normalize_https_url(
            first_value(
                item,
                (
                    "eyecatch",
                    "eyeCatch",
                    "thumbnailExternalUrl",
                    "thumbnail_external_url",
                    "imageUrl",
                    "image_url",
                ),
            )
        )

        posts.append(
            Post(
                title=title,
                url=url,
                published=published,
                excerpt=excerpt,
                source_image=image,
            )
        )

    posts.sort(key=lambda post: post.published, reverse=True)
    return posts[:MAX_POSTS]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def first_xml_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = {name.lower() for name in names}
    for child in list(element):
        if local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""


def extract_rss_image(item: ET.Element, html_sources: Iterable[str]) -> str:
    for child in item.iter():
        name = local_name(child.tag)
        if name in {"thumbnail", "content", "enclosure"}:
            url = normalize_https_url(child.attrib.get("url") or "")
            media_type = (child.attrib.get("type") or "").lower()
            if url and (
                name != "enclosure"
                or not media_type
                or media_type.startswith("image/")
            ):
                return url

    for source in html_sources:
        match = IMG_RE.search(source or "")
        if match:
            return normalize_https_url(match.group(1))
    return ""


def parse_rss_posts(xml_bytes: bytes) -> list[Post]:
    root = ET.fromstring(xml_bytes)
    items = [
        element
        for element in root.iter()
        if local_name(element.tag) in {"item", "entry"}
    ]

    posts: list[Post] = []
    for item in items:
        title = first_xml_text(item, {"title"})
        url = first_xml_text(item, {"link"})
        if not url:
            for child in list(item):
                if local_name(child.tag) == "link":
                    url = (child.attrib.get("href") or "").strip()
                    if url:
                        break
        url = normalize_https_url(url)
        if not title or not url:
            continue

        published = parse_datetime(
            first_xml_text(item, {"pubdate", "published", "updated", "date"})
        )
        description = first_xml_text(item, {"description", "summary"})
        content = first_xml_text(item, {"encoded", "content"})

        posts.append(
            Post(
                title=title,
                url=url,
                published=published,
                excerpt=strip_html(description or content),
                source_image=extract_rss_image(item, (content, description)),
            )
        )

    posts.sort(key=lambda post: post.published, reverse=True)
    return posts[:MAX_POSTS]


def fetch_posts() -> list[Post]:
    try:
        posts = parse_api_posts(fetch_json(API_URL))
        if posts:
            print(f"Fetched {len(posts)} post(s) from note contents API.")
            return posts
        raise RuntimeError("API returned no usable posts")
    except Exception as api_error:
        print(f"WARNING: note contents API failed: {api_error}", file=sys.stderr)

    rss_bytes, _ = request_bytes(
        RSS_URL,
        accept="application/rss+xml,application/xml,text/xml,*/*",
        max_bytes=6 * 1024 * 1024,
    )
    posts = parse_rss_posts(rss_bytes)
    if not posts:
        raise RuntimeError("Neither note API nor RSS returned usable posts")
    print(f"Fetched {len(posts)} post(s) from RSS fallback.")
    return posts


def article_id(article_url: str) -> str:
    last = urllib.parse.urlparse(article_url).path.rstrip("/").rsplit("/", 1)[-1]
    cleaned = SAFE_ID_RE.sub("-", last).strip("-")
    if cleaned:
        return cleaned[:80]
    return hashlib.sha256(article_url.encode("utf-8")).hexdigest()[:20]


def extension_from_magic(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    if data.startswith(b"<svg") or b"<svg" in data[:300]:
        return ".svg"
    if len(data) >= 12 and data[4:12] in {b"ftypavif", b"ftypavis"}:
        return ".avif"
    return ""


def extension_for(content_type: str, image_url: str, data: bytes) -> str:
    content_type = content_type.split(";", 1)[0].strip().lower()
    if content_type in IMAGE_EXTENSIONS:
        return IMAGE_EXTENSIONS[content_type]

    magic = extension_from_magic(data)
    if magic:
        return magic

    guessed = (
        mimetypes.guess_extension(content_type)
        if content_type.startswith("image/")
        else None
    )
    if guessed:
        return ".jpg" if guessed == ".jpe" else guessed

    path_ext = Path(urllib.parse.urlparse(image_url).path).suffix.lower()
    if path_ext in {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}:
        return ".jpg" if path_ext == ".jpeg" else path_ext

    raise RuntimeError(f"unsupported image type: {content_type or 'unknown'}")


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
        if (
            isinstance(item, dict)
            and isinstance(item.get("url"), str)
            and isinstance(item.get("image"), str)
        ):
            result[item["url"]] = item["image"]
    return result


def previous_local_file(web_path: str, image_dir: Path) -> Path | None:
    prefix = "../assets/note-images/"
    if not isinstance(web_path, str) or not web_path.startswith(prefix):
        return None
    candidate = image_dir / web_path.rsplit("/", 1)[-1]
    return candidate if candidate.is_file() else None


def cache_post_image(
    post: Post,
    image_dir: Path,
    previous: dict[str, str],
) -> Post:
    if post.source_image:
        try:
            data, content_type = request_bytes(
                post.source_image,
                accept="image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                referer=post.url,
            )
            if not content_type.startswith("image/") and not extension_from_magic(data):
                raise RuntimeError(f"not an image ({content_type or 'unknown'})")

            ext = extension_for(content_type, post.source_image, data)
            filename = f"{article_id(post.url)}{ext}"
            destination = image_dir / filename
            write_if_changed(destination, data)

            return replace(
                post,
                local_image=f"../assets/note-images/{filename}",
            )
        except Exception as exc:
            print(
                f"WARNING: local image download failed for {post.source_image}: {exc}",
                file=sys.stderr,
            )

    old = previous_local_file(previous.get(post.url, ""), image_dir)
    if old:
        print(f"Keeping previous local image for {post.title}.")
        return replace(post, local_image=f"../assets/note-images/{old.name}")

    # Important: use note's eyecatch URL before the fallback SVG.
    # The browser can often display it even when the Actions runner could not cache it.
    if post.source_image:
        print(f"Using external eyecatch URL for {post.title}.")
        return replace(post, local_image=post.source_image)

    return replace(post, local_image=FALLBACK_WEB_PATH)


def cleanup_stale_images(image_dir: Path, active_web_paths: set[str]) -> None:
    active_names = {
        path.rsplit("/", 1)[-1]
        for path in active_web_paths
        if isinstance(path, str) and "/note-images/" in path
    }
    if not image_dir.exists():
        return

    for path in image_dir.iterdir():
        if (
            path.is_file()
            and path.name not in active_names
            and path.name != ".gitkeep"
        ):
            path.unlink()


def serialize(posts: list[Post]) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    serialized = []

    for post in posts[:MAX_POSTS]:
        local = post.published.astimezone(JST)
        serialized.append(
            {
                "title": post.title,
                "url": post.url,
                "date_iso": local.date().isoformat(),
                "date_display": local.strftime("%Y.%m.%d"),
                "excerpt": post.excerpt,
                "image": post.local_image or post.source_image or FALLBACK_WEB_PATH,
                "source_image": post.source_image,
            }
        )

    return {
        "source": API_URL,
        "rss_fallback": RSS_URL,
        "updated_at": now.isoformat(timespec="seconds"),
        "posts": serialized,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    parser.add_argument(
        "--input-json",
        type=Path,
        help="Testing only: parse a saved note API response instead of downloading",
    )
    args = parser.parse_args()

    try:
        if args.input_json:
            payload = json.loads(args.input_json.read_text(encoding="utf-8"))
            posts = parse_api_posts(payload)
        else:
            posts = fetch_posts()

        if not posts:
            raise RuntimeError("No valid F-tec note posts were found")

        previous = load_previous_images(args.output)
        cached = [
            cache_post_image(post, args.image_dir, previous)
            for post in posts[:MAX_POSTS]
        ]

        payload = serialize(cached)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        cleanup_stale_images(
            args.image_dir,
            {post.local_image for post in cached},
        )

        local_count = sum(
            1 for post in cached if "/note-images/" in post.local_image
        )
        external_count = sum(
            1 for post in cached if post.local_image.startswith("https://")
        )
        fallback_count = sum(
            1 for post in cached if post.local_image == FALLBACK_WEB_PATH
        )

        print(
            f"Updated {args.output}: "
            f"{len(cached)} posts, "
            f"{local_count} local images, "
            f"{external_count} external images, "
            f"{fallback_count} fallback images."
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
