/* F-tec lightweight hotfix v11 */
(() => {
  'use strict';

  const MENU = '.mobile-menu';
  const ARROWS = /[→↗➜➝➞⟶⟹⇢⇥›»＞﹥⤴➡➤➥➦➧➨➩➪➫➬➭➮➯➱⮕]/gu;
  const VARIATION = /[\uFE0E\uFE0F]/gu;
  let scheduled = false;

  const cleanTextNodes = (link) => {
    const walker = document.createTreeWalker(link, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      node.nodeValue = (node.nodeValue || '').replace(ARROWS, '').replace(VARIATION, '');
    });
  };

  const removeOldArrowElements = (link) => {
    link.querySelectorAll([
      'svg',
      '[aria-hidden="true"]',
      '.ftec-hotfix-arrow-host-v5', '.ftec-hotfix-arrow-host-v7',
      '.ftec-hotfix-arrow-host-v8', '.ftec-hotfix-arrow-host-v9',
      '.ftec-hotfix-inline-arrow-v5', '.ftec-hotfix-inline-arrow-v7',
      '.ftec-hotfix-inline-arrow-v8', '.ftec-hotfix-inline-arrow-v9',
      '.ftec-hotfix-menu-arrow-v5', '.ftec-hotfix-menu-arrow-v7',
      '.ftec-hotfix-menu-arrow-v8', '.ftec-hotfix-menu-arrow-v9',
      '.ftec-v10-menu-arrow'
    ].join(',')).forEach((element) => element.remove());
  };

  const normalizeLink = (link) => {
    if (!(link instanceof HTMLAnchorElement)) return;
    removeOldArrowElements(link);
    cleanTextNodes(link);
    const label = (link.textContent || '').replace(/\s+/g, ' ').trim();
    link.classList.toggle('ftec-v11-goods', label === 'グッズ販売');
  };

  const normalize = () => {
    document.querySelectorAll(`${MENU} a`).forEach(normalizeLink);
    document.documentElement.dataset.ftecHotfixVersion = '11';
  };

  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      normalize();
    });
  };

  const start = () => {
    normalize();
    const observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, { childList: true, subtree: true });
    [0, 50, 250, 1000, 2500].forEach((delay) => setTimeout(normalize, delay));
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
