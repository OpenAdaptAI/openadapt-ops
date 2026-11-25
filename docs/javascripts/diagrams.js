/* Lightweight interactive step highlighting for unified OpenAdapt SVG diagrams.
 * Respects prefers-reduced-motion and Material's navigation.instant (document$). */
(function () {
  function bindDiagrams() {
    var frames = document.querySelectorAll('.oa-diagram-frame svg');
    frames.forEach(function (svg) {
      if (svg.dataset.oaBound === '1') return;
      svg.dataset.oaBound = '1';
      var nodes = svg.querySelectorAll('.oa-svg-node');
      if (!nodes.length) return;

      function activate(node) {
        svg.classList.add('oa-diagram-has-active');
        nodes.forEach(function (n) {
          n.classList.toggle('is-active', n === node);
        });
      }

      function clear() {
        svg.classList.remove('oa-diagram-has-active');
        nodes.forEach(function (n) {
          n.classList.remove('is-active');
        });
      }

      nodes.forEach(function (node) {
        if (!node.hasAttribute('tabindex')) node.setAttribute('tabindex', '0');
        node.addEventListener('mouseenter', function () { activate(node); });
        node.addEventListener('focus', function () { activate(node); });
        node.addEventListener('mouseleave', clear);
        node.addEventListener('blur', clear);
      });
    });
  }

  if (typeof document$ !== 'undefined' && document$ && typeof document$.subscribe === 'function') {
    document$.subscribe(bindDiagrams);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindDiagrams);
  } else {
    bindDiagrams();
  }
})();
