/* F-tec lightweight hotfix v14 */
(() => {
  'use strict';

  const MENU_SELECTOR = '.mobile-menu';
  const ARROW_CHARS = /[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴➡➤➥➦➧➨➩➪➫➬➭➮➯➱⮕]/gu;
  const EXTERNAL_HOSTS = [
    'note.com', 'x.com', 'twitter.com', 'instagram.com', 'facebook.com',
    'line.me', 'lin.ee', 'youtube.com', 'youtu.be'
  ];
  let scheduled = false;

  function isExternalLink(link) {
    if (link.target === '_blank') return true;
    const raw = link.getAttribute('href') || '';
    if (!raw || raw.startsWith('#') || raw.startsWith('mailto:') || raw.startsWith('tel:')) return false;
    try {
      const url = new URL(raw, location.href);
      if (EXTERNAL_HOSTS.some((host) => url.hostname === host || url.hostname.endsWith(`.${host}`))) return true;
      return url.origin !== location.origin;
    } catch (_) {
      return false;
    }
  }

  function removeOldArrows(link) {
    link.querySelectorAll(
      'svg, [aria-hidden="true"], [class*="arrow"], [class*="Arrow"], [class*="hotfix"]'
    ).forEach((node) => {
      const text = (node.textContent || '').trim();
      if (node.tagName.toLowerCase() === 'svg' || !text || ARROW_CHARS.test(text)) node.remove();
      ARROW_CHARS.lastIndex = 0;
    });

    const walker = document.createTreeWalker(link, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      node.nodeValue = (node.nodeValue || '')
        .replace(ARROW_CHARS, '')
        .replace(/[\uFE0E\uFE0F]/gu, '');
      ARROW_CHARS.lastIndex = 0;
    });
  }

  function fixLink(link) {
    if (!(link instanceof HTMLAnchorElement)) return;
    removeOldArrows(link);

    const label = (link.textContent || '').replace(/\s+/g, ' ').trim();
    link.dataset.ftecMenuLink = 'true';
    link.toggleAttribute('data-ftec-external', isExternalLink(link));
    link.toggleAttribute('data-ftec-goods', label === 'グッズ販売');
    link.toggleAttribute('data-ftec-contact', label === 'お問い合わせ');
  }

  function apply() {
    document.querySelectorAll(`${MENU_SELECTOR} a`).forEach(fixLink);
    document.documentElement.dataset.ftecHotfixVersion = '14';
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      apply();
    });
  }

  function start() {
    apply();
    const observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
    [0, 50, 250, 1000, 2500].forEach((delay) => setTimeout(apply, delay));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
