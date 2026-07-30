(() => {
  'use strict';

  const SECTION_SELECTOR = '#latest';
  const GRID_SELECTOR = '.note-post-grid';
  const DATA_URL = '../assets/note-latest.json';
  const MAX_POSTS = 3;

  function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = text;
    return element;
  }

  function normalizeUrl(value) {
    try {
      const url = new URL(value, window.location.href);
      if (url.protocol !== 'https:' && url.protocol !== 'http:') return '';
      return url.href;
    } catch {
      return '';
    }
  }

  function createCard(post, index) {
    const href = normalizeUrl(post.url);
    if (!href) return null;

    const card = createElement('a', 'note-post-card');
    if (index === 0) card.classList.add('note-post-card--feature');
    card.href = href;
    card.target = '_blank';
    card.rel = 'noreferrer';

    const imageBox = createElement('div', 'note-post-card__image');
    const imageUrl = normalizeUrl(post.image);
    if (imageUrl) {
      const image = document.createElement('img');
      image.src = imageUrl;
      image.alt = `${post.title || 'note記事'}の見出し画像`;
      image.loading = 'lazy';
      image.decoding = 'async';
      image.referrerPolicy = 'no-referrer';
      imageBox.appendChild(image);
    } else {
      imageBox.setAttribute('aria-hidden', 'true');
      imageBox.style.background = 'linear-gradient(135deg, #e8eef8, #b9c9e5)';
    }

    const body = createElement('div', 'note-post-card__body');
    const meta = createElement('div', 'note-post-card__meta');
    const time = createElement('time', '', post.date_display || '');
    if (post.date_iso) time.dateTime = post.date_iso;
    meta.append(time, createElement('span', '', 'note'));

    const title = createElement('h3', '', post.title || '最新の記事');
    const excerpt = createElement('p', '', post.excerpt || '');
    const arrow = createElement('b', '', '↗');
    arrow.setAttribute('aria-hidden', 'true');

    body.append(meta, title, excerpt, arrow);
    card.append(imageBox, body);
    return card;
  }

  async function updateLatestNotePosts() {
    const section = document.querySelector(SECTION_SELECTOR);
    const grid = section?.querySelector(GRID_SELECTOR);
    if (!grid) return;

    try {
      const response = await fetch(`${DATA_URL}?v=${Date.now()}`, {
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      if (!Array.isArray(data.posts) || data.posts.length === 0) return;

      const fragment = document.createDocumentFragment();
      data.posts.slice(0, MAX_POSTS).forEach((post, index) => {
        const card = createCard(post, index);
        if (card) fragment.appendChild(card);
      });

      if (!fragment.childNodes.length) return;
      grid.replaceChildren(fragment);
      section.dataset.noteUpdatedAt = data.updated_at || '';
    } catch (error) {
      // RSS更新に失敗した場合は、HTMLに保存済みの既存カードをそのまま表示する。
      console.warn('note最新記事の読み込みに失敗しました。既存表示を使用します。', error);
    }
  }

  updateLatestNotePosts();
})();
