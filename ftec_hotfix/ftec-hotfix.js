/* F-tec inline hotfix v17 */
(() => {
  'use strict';

  const VERSION = '17';
  const MENU = '.mobile-menu';
  const ARROW_CHARS = '←→↗➡➜➝➞⟶⟹⇢⇥›»＞﹥⤴➤➥➦➧➨➩➪➫➬➭➮➯➱⮕';
  const ARROW_RE = new RegExp(`[${ARROW_CHARS}\\uFE0E\\uFE0F]`, 'gu');
  const ARROW_ONLY_RE = new RegExp(`^[\\s${ARROW_CHARS}\\uFE0E\\uFE0F]+$`, 'u');
  const EXTERNAL_HOSTS = [
    'note.com', 'x.com', 'twitter.com', 'instagram.com', 'facebook.com',
    'line.me', 'lin.ee', 'youtube.com', 'youtu.be'
  ];
  let queued = false;
  let observer = null;

  function isExternal(link) {
    const href = link.getAttribute('href') || '';
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return false;
    try {
      const url = new URL(href, location.href);
      return EXTERNAL_HOSTS.some((host) => url.hostname === host || url.hostname.endsWith('.' + host)) || url.origin !== location.origin;
    } catch (_) {
      return false;
    }
  }

  function svgMarkup(kind) {
    if (kind === 'external') {
      return '<svg class="ftec-arrow-svg" viewBox="0 0 18 18" aria-hidden="true" focusable="false"><path d="M4 14L14 4M7 4h7v7"/></svg>';
    }
    if (kind === 'left') {
      return '<svg class="ftec-arrow-svg" viewBox="0 0 24 14" aria-hidden="true" focusable="false"><path d="M23 7H2M7 2L2 7l5 5"/></svg>';
    }
    return '<svg class="ftec-arrow-svg" viewBox="0 0 24 14" aria-hidden="true" focusable="false"><path d="M1 7h21M17 2l5 5-5 5"/></svg>';
  }

  function makeSlot(kind) {
    const slot = document.createElement('span');
    slot.className = 'ftec-arrow-slot';
    slot.setAttribute('aria-hidden', 'true');
    slot.dataset.ftecArrowKind = kind;
    slot.innerHTML = svgMarkup(kind);
    return slot;
  }

  function glyphsOutsideSlot(element) {
    let glyph = '';
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      if (walker.currentNode.parentElement?.closest('.ftec-arrow-slot')) continue;
      const match = (walker.currentNode.nodeValue || '').match(ARROW_RE);
      if (match) glyph += match.join('');
      ARROW_RE.lastIndex = 0;
    }
    return glyph;
  }

  function hasLegacyArrowNode(element) {
    return [...element.querySelectorAll('span, i, b, em, strong, small')].some((node) => {
      if (node.classList.contains('ftec-arrow-slot')) return false;
      const text = (node.textContent || '').trim();
      return Boolean(text && ARROW_ONLY_RE.test(text));
    });
  }

  function removeLegacyArrows(element) {
    element.querySelectorAll('.ftec-arrow-slot').forEach((node) => node.remove());
    element.querySelectorAll('span, i, b, em, strong, small').forEach((node) => {
      if (node.classList.contains('ftec-arrow-slot')) return;
      const text = (node.textContent || '').trim();
      if (text && ARROW_ONLY_RE.test(text)) node.remove();
    });
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach((node) => {
      node.nodeValue = (node.nodeValue || '').replace(ARROW_RE, '');
      ARROW_RE.lastIndex = 0;
    });
  }

  function normalizeLink(link, force = false) {
    if (!(link instanceof HTMLAnchorElement)) return;
    const glyph = glyphsOutsideSlot(link);
    const kind = isExternal(link) ? 'external' : (glyph.includes('←') ? 'left' : 'right');
    const slots = [...link.querySelectorAll(':scope > .ftec-arrow-slot')];
    const ready = link.dataset.ftecArrowReady === 'true';
    const needsArrow = force || Boolean(glyph) || slots.length > 0 || ready;
    if (!needsArrow) return;

    const clean = !glyph && !hasLegacyArrowNode(link) && slots.length === 1 &&
      slots[0].dataset.ftecArrowKind === kind;
    if (!clean) {
      const wasOnlyArrow = (link.textContent || '').replace(ARROW_RE, '').trim() === '';
      ARROW_RE.lastIndex = 0;
      removeLegacyArrows(link);
      link.appendChild(makeSlot(kind));
      if (wasOnlyArrow) link.dataset.ftecArrowOnly = 'true';
      else delete link.dataset.ftecArrowOnly;
    }

    link.dataset.ftecArrowReady = 'true';
    link.dataset.ftecArrowKind = kind;

    if (link.closest(MENU)) {
      link.dataset.ftecMenuLink = 'true';
      if (kind === 'external') link.dataset.ftecExternal = 'true';
      else delete link.dataset.ftecExternal;
      const label = (link.textContent || '').replace(/\s+/g, ' ').trim();
      if (label === 'グッズ販売') link.dataset.ftecGoods = 'true';
      else delete link.dataset.ftecGoods;
      if (label === 'お問い合わせ') link.dataset.ftecContact = 'true';
      else delete link.dataset.ftecContact;
    }
  }

  function normalizeArrowButton(button) {
    if (!(button instanceof HTMLButtonElement)) return;
    const glyph = glyphsOutsideSlot(button);
    const slots = [...button.querySelectorAll(':scope > .ftec-arrow-slot')];
    const ready = button.dataset.ftecArrowReady === 'true';
    if (!glyph && slots.length === 0 && !ready) return;
    const kind = glyph.includes('←') ? 'left' : (button.dataset.ftecArrowKind || 'right');
    const clean = !glyph && !hasLegacyArrowNode(button) && slots.length === 1 &&
      slots[0].dataset.ftecArrowKind === kind;
    if (!clean) {
      const wasOnlyArrow = (button.textContent || '').replace(ARROW_RE, '').trim() === '';
      ARROW_RE.lastIndex = 0;
      removeLegacyArrows(button);
      button.appendChild(makeSlot(kind));
      if (wasOnlyArrow) button.dataset.ftecArrowOnly = 'true';
      else delete button.dataset.ftecArrowOnly;
    }
    button.dataset.ftecArrowReady = 'true';
    button.dataset.ftecArrowKind = kind;
  }

  function observe() {
    if (!observer) observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  function apply() {
    observer?.disconnect();
    document.querySelectorAll('a').forEach((link) => normalizeLink(link, Boolean(link.closest(MENU))));
    document.querySelectorAll('button').forEach(normalizeArrowButton);
    document.documentElement.setAttribute('data-ftec-inline-hotfix', VERSION);
    observe();
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
    [50, 250, 1000, 2500].forEach((ms) => setTimeout(apply, ms));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
