(() => {
  'use strict';

  const DATA_URL = 'assets/note-latest.json';
  const FALLBACK_IMAGE = 'assets/note-fallback.svg';
  const MAX_POSTS = 3;

  const createElement = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined && text !== null) el.textContent = text;
    return el;
  };

  const normalizeUrl = (value) => {
    try {
      const url = new URL(value, window.location.href);
      if (url.protocol !== 'https:' && url.protocol !== 'http:') return '';
      return url.href;
    } catch {
      return '';
    }
  };

  const normalizeImageUrl = (value) => {
    if (typeof value !== 'string' || !value) {
      return normalizeUrl(FALLBACK_IMAGE);
    }

    // activity/ 側の JSON は ../assets/... を使うため、
    // トップページでは assets/... に直す。
    if (value.startsWith('../assets/')) {
      return normalizeUrl(value.slice(3));
    }

    if (value.startsWith('./')) {
      return normalizeUrl(value.slice(2));
    }

    return normalizeUrl(value);
  };

  const createCard = (post, index) => {
    const href = normalizeUrl(post.url);
    if (!href) return null;

    const title = post.title || '最新の記事';

    const article = createElement('article', 'news-card');

    const imageLink = createElement('a', 'news-card__image');
    imageLink.href = href;
    imageLink.target = '_blank';
    imageLink.rel = 'noopener noreferrer';
    imageLink.setAttribute('aria-label', `${title}をnoteで読む`);

    const image = document.createElement('img');
    image.src = normalizeImageUrl(post.image) || normalizeUrl(FALLBACK_IMAGE);
    image.alt = `${title}の見出し画像`;
    image.loading = 'lazy';
    image.decoding = 'async';
    image.addEventListener(
      'error',
      () => {
        const fallback = normalizeUrl(FALLBACK_IMAGE);
        if (fallback && image.src !== fallback) image.src = fallback;
      },
      { once: true }
    );
    imageLink.appendChild(image);

    const top = createElement('div', 'news-card__top');
    top.append(
      createElement('span', '', String(index + 1).padStart(2, '0')),
      createElement('p', '', 'F-TEC NOTE')
    );

    const body = document.createElement('div');

    const time = createElement(
      'time',
      '',
      post.date_display || post.date_iso || ''
    );

    if (post.date_iso) {
      time.dateTime = post.date_iso;
    }

    body.append(
      time,
      createElement('h3', '', title),
      createElement('p', '', post.excerpt || '')
    );

    const arrow = createElement('a', '', '↗');
    arrow.href = href;
    arrow.target = '_blank';
    arrow.rel = 'noopener noreferrer';
    arrow.setAttribute('aria-label', `${title}をnoteで読む`);

    article.append(imageLink, top, body, arrow);
    return article;
  };

  const updateLatestActivity = async () => {
    const grid = document.querySelector('.news-section .news-grid');
    if (!grid) return;

    try {
      const response = await fetch(`${DATA_URL}?v=${Date.now()}`, {
        cache: 'no-store',
        headers: {
          Accept: 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!Array.isArray(data.posts) || data.posts.length === 0) {
        return;
      }

      const fragment = document.createDocumentFragment();

      data.posts.slice(0, MAX_POSTS).forEach((post, index) => {
        const card = createCard(post, index);
        if (card) fragment.appendChild(card);
      });

      if (!fragment.childNodes.length) return;

      grid.replaceChildren(fragment);
      grid.dataset.noteUpdatedAt = data.updated_at || '';
    } catch (error) {
      // JSON取得に失敗した場合は、index.html に元から書かれている
      // 3件の記事をそのままフォールバック表示する。
      console.warn(
        'ホームの最新活動を更新できませんでした。静的表示を使用します。',
        error
      );
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateLatestActivity, {
      once: true,
    });
  } else {
    updateLatestActivity();
  }
})();
