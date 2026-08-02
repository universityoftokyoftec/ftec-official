/* F-tec inline hotfix v15 */
(() => {
  'use strict';

  const MENU = '.mobile-menu';
  const ARROWS = /[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴➡➤➥➦➧➨➩➪➫➬➭➮➯➱⮕]/gu;
  const EXTERNAL_HOSTS = [
    'note.com', 'x.com', 'twitter.com', 'instagram.com', 'facebook.com',
    'line.me', 'lin.ee', 'youtube.com', 'youtu.be'
  ];
  let queued = false;

  function external(link) {
    if (link.target === '_blank') return true;
    const href = link.getAttribute('href') || '';
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return false;
    try {
      const url = new URL(href, location.href);
      return EXTERNAL_HOSTS.some((host) => url.hostname === host || url.hostname.endsWith('.' + host)) || url.origin !== location.origin;
    } catch (_) {
      return false;
    }
  }

  function removeArrowChildren(link) {
    link.querySelectorAll('svg, [aria-hidden="true"], [class*="arrow" i]').forEach((node) => {
      const text = (node.textContent || '').trim();
      if (node.tagName.toLowerCase() === 'svg' || !text || ARROWS.test(text)) node.remove();
      ARROWS.lastIndex = 0;
    });

    const walker = document.createTreeWalker(link, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach((node) => {
      node.nodeValue = (node.nodeValue || '').replace(ARROWS, '').replace(/[\uFE0E\uFE0F]/gu, '');
      ARROWS.lastIndex = 0;
    });
  }

  function fix(link) {
    if (!(link instanceof HTMLAnchorElement)) return;
    removeArrowChildren(link);
    const label = (link.textContent || '').replace(/\s+/g, ' ').trim();
    link.setAttribute('data-ftec-menu-link', 'true');
    if (external(link)) link.setAttribute('data-ftec-external', 'true');
    else link.removeAttribute('data-ftec-external');
    if (label === 'グッズ販売') link.setAttribute('data-ftec-goods', 'true');
    else link.removeAttribute('data-ftec-goods');
    if (label === 'お問い合わせ') link.setAttribute('data-ftec-contact', 'true');
    else link.removeAttribute('data-ftec-contact');
  }

  function apply() {
    document.querySelectorAll(`${MENU} a`).forEach(fix);
    document.documentElement.setAttribute('data-ftec-inline-hotfix', '15');
  }

  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      apply();
    });
  }

  function start() {
    apply();
    new MutationObserver(schedule).observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true
    });
    [0, 50, 250, 1000, 2500].forEach((ms) => setTimeout(apply, ms));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
