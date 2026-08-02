/* F-tec mobile navigation hotfix v7 */
(() => {
  'use strict';

  const MENU_SELECTOR = '.mobile-menu';
  const ARROW_CHARS = /^[\s→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴︎↗︎↗️]+$/u;
  let scheduled = false;

  const normalizedText = (node) =>
    (node.textContent || '')
      .replace(/[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴︎]/gu, '')
      .replace(/\s+/g, ' ')
      .trim();

  const isLegacyArrow = (element) => {
    if (!(element instanceof HTMLElement) && !(element instanceof SVGElement)) return false;
    if (element.classList.contains('ftec-hotfix-arrow-v7')) return true;

    const text = (element.textContent || '').trim();
    const ariaHidden = element.getAttribute('aria-hidden') === 'true';
    const likelyArrowClass = /arrow|icon|external|chevron/i.test(element.className?.baseVal || element.className || '');

    return (
      (text && text.length <= 4 && ARROW_CHARS.test(text)) ||
      (ariaHidden && text.length <= 4) ||
      (likelyArrowClass && text.length <= 4)
    );
  };

  const removeLegacyArrows = (link) => {
    [...link.children].forEach((child) => {
      if (isLegacyArrow(child)) child.remove();
    });

    /* 矢印だけのテキストノードにも対応 */
    [...link.childNodes].forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const value = node.nodeValue || '';
        if (value.trim() && ARROW_CHARS.test(value.trim())) node.remove();
      }
    });
  };

  const createArrow = (external) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', external ? '0 0 18 18' : '0 0 24 14');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.classList.add('ftec-hotfix-arrow-v7');
    if (external) svg.classList.add('is-external');

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute(
      'd',
      external ? 'M4 14L14 4M7 4H14V11' : 'M1 7H22M17 2L22 7L17 12'
    );
    svg.appendChild(path);
    return svg;
  };

  const setImportant = (element, property, value) => {
    element.style.setProperty(property, value, 'important');
  };

  const styleGoodsLink = (link) => {
    link.classList.add('ftec-hotfix-top-link-v7');
    setImportant(link, 'display', 'flex');
    setImportant(link, 'align-items', 'center');
    setImportant(link, 'justify-content', 'space-between');
    setImportant(link, 'gap', '20px');
    setImportant(link, 'width', '100%');
    setImportant(link, 'margin', '0');
    setImportant(link, 'padding', '18px 0');
    setImportant(link, 'border', '0');
    setImportant(link, 'border-bottom', '1px solid rgba(255,255,255,.18)');
    setImportant(link, 'border-radius', '0');
    setImportant(link, 'background', 'transparent');
    setImportant(link, 'color', '#fff');
    setImportant(link, 'font-size', 'clamp(18px, 5vw, 25px)');
    setImportant(link, 'font-weight', '600');
    setImportant(link, 'line-height', '1.45');
    setImportant(link, 'letter-spacing', '.02em');
  };

  const fixLink = (link) => {
    if (!(link instanceof HTMLAnchorElement)) return;

    const labelBefore = normalizedText(link);
    removeLegacyArrows(link);

    link.classList.remove(
      'ftec-hotfix-top-link-v7',
      'ftec-hotfix-sub-link-v7',
      'ftec-hotfix-contact-v7'
    );

    if (labelBefore === 'グッズ販売') {
      styleGoodsLink(link);
    } else if (labelBefore === 'お問い合わせ') {
      link.classList.add('ftec-hotfix-contact-v7');
    } else {
      link.classList.add('ftec-hotfix-sub-link-v7');
    }

    const external = link.target === '_blank' || /^(https?:)?\/\//i.test(link.getAttribute('href') || '');
    link.appendChild(createArrow(external));
    link.dataset.ftecHotfixV7 = 'done';
  };

  const fixMenu = () => {
    const menu = document.querySelector(MENU_SELECTOR);
    if (!menu) return;

    menu.querySelectorAll('a').forEach(fixLink);
    menu.dataset.ftecHotfixVersion = '7';
    document.documentElement.dataset.ftecHotfixVersion = '7';
  };

  const scheduleFix = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      fixMenu();
    });
  };



  /*
   * iOS/Safari may render U+2197 and related arrows as colorful emoji.
   * Force the Unicode text presentation selector (U+FE0E) everywhere,
   * including content inserted after page load.
   */
  const EMOJI_PRONE_ARROWS = /([\u2196\u2197\u2198\u2199\u2934\u2935\u2B05\u2B06\u2B07\u27A1])[\uFE0E\uFE0F]?/gu;

  const forceTextArrowPresentation = (root = document.body) => {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/i.test(parent.tagName)) {
          return NodeFilter.FILTER_REJECT;
        }
        return EMOJI_PRONE_ARROWS.test(node.nodeValue || '')
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      }
    });

    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      EMOJI_PRONE_ARROWS.lastIndex = 0;
      node.nodeValue = (node.nodeValue || '').replace(EMOJI_PRONE_ARROWS, '$1\uFE0E');
    });
  };

  const start = () => {
    forceTextArrowPresentation(document.body);
    fixMenu();

    const observer = new MutationObserver((mutations) => {
      const relevant = mutations.some((mutation) =>
        [...mutation.addedNodes].some((node) =>
          node.nodeType === Node.ELEMENT_NODE &&
          (node.matches?.(MENU_SELECTOR) || node.querySelector?.(MENU_SELECTOR) || node.closest?.(MENU_SELECTOR))
        )
      );
      forceTextArrowPresentation(document.body);
      if (relevant) scheduleFix();
    });

    observer.observe(document.documentElement, { childList: true, subtree: true });

    /* 元スクリプトが遅れてメニューを再生成する場合の保険 */
    setTimeout(() => { forceTextArrowPresentation(document.body); fixMenu(); }, 0);
    setTimeout(() => { forceTextArrowPresentation(document.body); fixMenu(); }, 250);
    setTimeout(() => { forceTextArrowPresentation(document.body); fixMenu(); }, 1000);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
