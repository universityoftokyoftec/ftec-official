/*
 * F-tec global patch script
 * HTML本体を触らずに済む軽微なDOM修正はこのファイルへ追記します。
 */
(() => {
  'use strict';

  const applyMobileMenuFixes = () => {
    document
      .querySelectorAll('.mobile-menu .ftec-mobile-links a > span[aria-hidden="true"]')
      .forEach((arrow) => {
        arrow.hidden = true;
        arrow.setAttribute('data-ftec-hidden-arrow', 'true');
      });
  };

  const start = () => {
    applyMobileMenuFixes();

    /* スマホメニューがJavaScriptで後から生成されても補正する */
    const observer = new MutationObserver((mutations) => {
      if (mutations.some((mutation) => mutation.addedNodes.length > 0)) {
        applyMobileMenuFixes();
      }
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
