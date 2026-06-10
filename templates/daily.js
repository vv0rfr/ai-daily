  /* ── theme ── */
  function toggleTheme() {
    var body = document.body;
    var btn = document.getElementById('themeBtn');
    body.classList.toggle('dark-mode');
    body.classList.remove('light-mode');
    btn.textContent = body.classList.contains('dark-mode') ? '☀' : '☾';
    try { localStorage.setItem('theme', body.classList.contains('dark-mode') ? 'dark' : 'light'); } catch(e) {}
  }
  try {
    if (localStorage.getItem('theme') === 'dark') {
      document.body.classList.add('dark-mode');
      document.getElementById('themeBtn').textContent = '☀';
    }
  } catch(e) {}

  /* ── bilingual toggle ── */
  function toggleLang(btn) {
    if (btn.disabled) return;
    var wrap = btn.closest('.hero, .acard, .vcard, .trend, .highlight');
    if (!wrap) return;
    var els = wrap.querySelectorAll('.bilingual');
    var isEn = btn.textContent.trim() === 'EN';
    els.forEach(function(el) {
      var target = isEn ? (el.dataset.en || el.dataset.zh) : el.dataset.zh;
      if (el.classList.contains('trend-body')) {
        el.innerHTML = target;
      } else {
        el.textContent = target;
      }
    });
    btn.textContent = isEn ? '中文' : 'EN';
  }

  /* ── copy link button ── */
  function copyLink() {
    var btn = document.querySelector('.btn-share');
    var url = (typeof PAGE_URL !== 'undefined' && PAGE_URL) ? PAGE_URL : window.location.href;
    function done() {
      btn.textContent = '已复制 ✓';
      btn.classList.add('copied');
      setTimeout(function() { btn.innerHTML = '&#x1F4CB; 复制本期链接'; btn.classList.remove('copied'); }, 2000);
    }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(done);
    } else {
      var ta = document.createElement('textarea');
      ta.value = url; document.body.appendChild(ta);
      ta.select(); document.execCommand('copy');
      document.body.removeChild(ta);
      done();
    }
  }

  /* ── progress bar + pill highlight ── */
  (function() {
    var bar = document.getElementById('progressBar');
    var pills = document.querySelectorAll('.pill[data-cat]');
    var sections = document.querySelectorAll('[data-cat]');
    var catColors = {
      '模型':'#0D9488','产品':'#2563EB','行业':'#C2410C',
      '论文':'#7C3AED','技巧':'#BE123C','视频':'#7C3AED'
    };
    function update() {
      var top = window.scrollY;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      if (bar) bar.style.width = (max > 0 ? Math.min(top / max * 100, 100) : 0) + '%';
      var current = '';
      for (var i = sections.length - 1; i >= 0; i--) {
        if (sections[i].getBoundingClientRect().top <= 120) {
          current = sections[i].dataset.cat; break;
        }
      }
      if (bar) bar.style.background = catColors[current] || '#C2410C';
      for (var j = 0; j < pills.length; j++) {
        pills[j].classList.toggle('active', pills[j].dataset.cat === current);
      }
    }
    window.addEventListener('scroll', update, {passive:true});
    update();
  })();

  /* ── smooth scroll for pills ── */
  document.addEventListener('click', function(e) {
    var pill = e.target.closest('.pill');
    if (!pill) return;
    e.preventDefault();
    var target = document.querySelector(pill.getAttribute('href'));
    if (target) {
      var y = target.getBoundingClientRect().top + window.scrollY - 50;
      window.scrollTo({top:y, behavior:'smooth'});
    }
  });

  /* ── row hover border color ── */
  document.addEventListener('mouseover', function(e) {
    var row = e.target.closest('.row');
    if (!row) return;
    var dot = row.querySelector('.row-dot');
    if (dot) row.style.borderLeftColor = dot.style.background;
  });
  document.addEventListener('mouseout', function(e) {
    var row = e.target.closest('.row');
    if (row) row.style.borderLeftColor = 'transparent';
  });