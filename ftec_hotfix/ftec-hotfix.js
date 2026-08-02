/* F-tec lightweight hotfix v12 */
(() => {
  'use strict';

  const VERSION = '12';
  const MENU = '.mobile-menu';
  const ARROW_CHARS = /[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴➡➤➥➦➧➨➩➪➫➬➭➮➯➱⮕]/gu;
  const ARROW_ONLY = /^\s*[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴➡➤➥➦➧➨➩➪➫➬➭➮➯➱⮕][\uFE0E\uFE0F]?\s*$/u;
  const EXTERNAL = /[↗⤴]/u;
  let queued = false;

  function makeArrow(external) {
    const host = document.createElement('span');
    host.className = `ftec-v12-arrow-host ${external ? 'is-external' : 'is-internal'}`;
    host.setAttribute('aria-hidden', 'true');

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', external ? '0 0 18 18' : '0 0 24 14');
    svg.setAttribute('focusable', 'false');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', external ? 'M4 14L14 4M7 4H14V11' : 'M1 7H22M17 2L22 7L17 12');
    svg.appendChild(path);
    host.appendChild(svg);
    return host;
  }

  function replaceGlobalArrows() {
    if (!document.body) return;

    /* 矢印だけを内容に持つ要素（span/i/a等）をSVG化。スマホメニューは別処理。 */
    document.querySelectorAll('span, i, b, em, strong, small, a, button').forEach((el) => {
      if (!(el instanceof HTMLElement)) return;
      if (el.closest(MENU)) return;
      if (el.classList.contains('ftec-v12-arrow-host')) return;
      if (el.children.length && ![...el.children].every((child) => child.matches('svg, path'))) return;
      const text = (el.textContent || '').trim();
      if (!ARROW_ONLY.test(text)) return;
      el.replaceChildren(makeArrow(EXTERNAL.test(text)));
    });

    /* 裸の矢印テキストノードもSVG化。 */
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const parent = node.parentElement;
      if (!parent || parent.closest(MENU)) return;
      if (/^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA|SVG|PATH)$/i.test(parent.tagName)) return;
      const text = node.nodeValue || '';
      if (!ARROW_ONLY.test(text.trim())) return;
      node.replaceWith(makeArrow(EXTERNAL.test(text)));
    });
  }

  function cleanMenuLink(link) {
    if (!(link instanceof HTMLAnchorElement)) return;

    /* 過去のSVG・矢印専用要素を削除。 */
    link.querySelectorAll('svg, .ftec-v12-arrow-host, [class*="hotfix"][class*="arrow"], [class*="menu-arrow"]').forEach((el) => el.remove());

    /* aria-hiddenの矢印文字要素だけ削除。 */
    link.querySelectorAll('[aria-hidden="true"]').forEach((el) => {
      const text = (el.textContent || '').trim();
      if (!text || ARROW_ONLY.test(text)) el.remove();
    });

    /* リンク内に直接残った矢印文字を消す。 */
    const walker = document.createTreeWalker(link, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach((node) => {
      node.nodeValue = (node.nodeValue || '').replace(ARROW_CHARS, '').replace(/[\uFE0E\uFE0F]/gu, '');
    });

    const label = (link.textContent || '').replace(/\s+/g, ' ').trim();
    link.classList.remove('ftec-v11-goods', 'ftec-v12-menu-link', 'ftec-v12-goods', 'ftec-v12-contact');
    if (label === 'グッズ販売') link.classList.add('ftec-v12-goods');
    else if (label === 'お問い合わせ') link.classList.add('ftec-v12-contact');
    else link.classList.add('ftec-v12-menu-link');
  }

  function fixMenu() {
    document.querySelectorAll(`${MENU} a`).forEach(cleanMenuLink);
  }

  function apply() {
    replaceGlobalArrows();
    fixMenu();
    document.documentElement.dataset.ftecHotfixVersion = VERSION;
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
    const observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
    [0, 50, 250, 1000, 2500].forEach((delay) => setTimeout(apply, delay));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
