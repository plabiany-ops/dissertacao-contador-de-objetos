(function () {
  var body = document.body;
  var toggle = document.querySelector('.menu-toggle');
  var overlay = document.querySelector('.overlay');

  function closeNav() {
    body.classList.remove('nav-open');
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      body.classList.toggle('nav-open');
    });
  }
  if (overlay) {
    overlay.addEventListener('click', closeNav);
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeNav();
  });

  var links = {};
  document.querySelectorAll('.toc a[href*="#"]').forEach(function (a) {
    var href = a.getAttribute('href') || '';
    var id = href.split('#')[1];
    if (!id) return;
    try { id = decodeURIComponent(id); } catch (e) {}
    var target = document.getElementById(id);
    if (target) links[id] = a;
  });

  var targets = Object.keys(links).map(function (id) {
    return document.getElementById(id);
  }).filter(Boolean);

  if ('IntersectionObserver' in window && targets.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        document.querySelectorAll('.toc a.active').forEach(function (a) {
          a.classList.remove('active');
        });
        var a = links[entry.target.id];
        if (a) a.classList.add('active');
      });
    }, { rootMargin: '-15% 0px -70% 0px', threshold: 0 });
    targets.forEach(function (t) { observer.observe(t); });
  }
})();
