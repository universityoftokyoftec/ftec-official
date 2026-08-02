/* F-tec lightweight hotfix v8 */
(() => {
  'use strict';

  const VERSION = '8';
  const MENU_SELECTOR = '.mobile-menu';
  const ARROW_ONLY = /^\s*([→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴])[\uFE0E\uFE0F]?\s*$/u;
  const EXTERNAL_ARROWS = /[↗⤴]/u;
  let scheduled = false;

  const makeSvg = (external, className) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', external ? '0 0 18 18' : '0 0 24 14');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.classList.add(className, external ? 'is-external' : 'is-internal');

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute(
      'd',
      external ? 'M4 14L14 4M7 4H14V11' : 'M1 7H22M17 2L22 7L17 12'
    );
    svg.appendChild(path);
    return svg;
  };

  const replaceStandaloneArrowElement = (element) => {
    if (!(element instanceof HTMLElement)) return;
    if (element.closest(MENU_SELECTOR)) return;
    if (element.querySelector('svg')) return;

    const match = (element.textContent || '').match(ARROW_ONLY);
    if (!match) return;

    const external = EXTERNAL_ARROWS.test(match[1]);
    element.replaceChildren(makeSvg(external, 'ftec-hotfix-inline-arrow-v8'));
    element.classList.add(
      'ftec-hotfix-arrow-host-v8',
      external ? 'is-external' : 'is-internal'
    );
  };

  const replaceStandaloneArrowTextNode = (node) => {
    if (node.nodeType !== Node.TEXT_NODE || !node.parentElement) return;
    if (node.parentElement.closest(MENU_SELECTOR)) return;
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA|SVG)$/i.test(node.parentElement.tagName)) return;

    const match = (node.nodeValue || '').match(ARROW_ONLY);
    if (!match) return;

    const external = EXTERNAL_ARROWS.test(match[1]);
    const host = document.createElement('span');
    host.setAttribute('aria-hidden', 'true');
    host.className = `ftec-hotfix-arrow-host-v8 ${external ? 'is-external' : 'is-internal'}`;
    host.appendChild(makeSvg(external, 'ftec-hotfix-inline-arrow-v8'));
    node.replaceWith(host);
  };

  const replaceGlobalGlyphArrows = (root = document.body) => {
    if (!root) return;

    root.querySelectorAll('span, i, b, em, strong, small').forEach(replaceStandaloneArrowElement);

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(replaceStandaloneArrowTextNode);
  };

  const normalizedText = (node) =>
    (node.textContent || '')
      .replace(/[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴]/gu, '')
      .replace(/\s+/g, ' ')
      .trim();

  const isLegacyMenuArrow = (element) => {
    if (!(element instanceof Element)) return false;
    if (element.matches('.ftec-hotfix-menu-arrow-v8, .ftec-hotfix-arrow-v5, .ftec-hotfix-arrow-v7, .ftec-hotfix-inline-arrow-v8')) return true;
    const text = (element.textContent || '').trim();
    return Boolean(text.match(ARROW_ONLY));
  };

  const removeLegacyMenuArrows = (link) => {
    [...link.children].forEach((child) => {
      if (isLegacyMenuArrow(child)) child.remove();
    });
    [...link.childNodes].forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE && (node.nodeValue || '').match(ARROW_ONLY)) node.remove();
    });
  };

  const setImportant = (element, property, value) => {
    element.style.setProperty(property, value, 'important');
  };

  const styleGoodsLink = (link) => {
    link.classList.add('ftec-hotfix-top-link-v8');
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

  const fixMenuLink = (link) => {
    if (!(link instanceof HTMLAnchorElement)) return;

    const label = normalizedText(link);
    removeLegacyMenuArrows(link);

    link.classList.remove(
      'ftec-hotfix-top-link-v5', 'ftec-hotfix-sub-link-v5', 'ftec-hotfix-contact-v5',
      'ftec-hotfix-top-link-v7', 'ftec-hotfix-sub-link-v7', 'ftec-hotfix-contact-v7',
      'ftec-hotfix-top-link-v8', 'ftec-hotfix-sub-link-v8', 'ftec-hotfix-contact-v8'
    );

    if (label === 'グッズ販売') {
      styleGoodsLink(link);
    } else if (label === 'お問い合わせ') {
      link.classList.add('ftec-hotfix-contact-v8');
    } else {
      link.classList.add('ftec-hotfix-sub-link-v8');
    }

    const external = link.target === '_blank' || /^(https?:)?\/\//i.test(link.getAttribute('href') || '');
    link.appendChild(makeSvg(external, 'ftec-hotfix-menu-arrow-v8'));
    link.dataset.ftecHotfixV8 = 'done';
  };

  const fixMenu = () => {
    document.querySelectorAll(`${MENU_SELECTOR} a`).forEach(fixMenuLink);
    document.documentElement.dataset.ftecHotfixVersion = VERSION;
  };

  const applyAll = () => {
    replaceGlobalGlyphArrows(document.body);
    fixMenu();
  };

  const scheduleApply = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      applyAll();
    });
  };

  const start = () => {
    applyAll();

    const observer = new MutationObserver((mutations) => {
      if (mutations.some((mutation) => mutation.addedNodes.length > 0)) scheduleApply();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });

    setTimeout(applyAll, 0);
    setTimeout(applyAll, 250);
    setTimeout(applyAll, 1000);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
