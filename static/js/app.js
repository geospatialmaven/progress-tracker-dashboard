/* ═══════════════════════════════════════════════
   GEOSPATIAL MAVEN — Dashboard JavaScript
   ═══════════════════════════════════════════════ */

// ─── THEME TOGGLE ────────────────────────────
function toggleTheme() {
  var root = document.getElementById('htmlRoot');
  var current = root.getAttribute('data-theme') || 'dark';
  var next = current === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  localStorage.setItem('gm-theme', next);
  _applyThemeIcon(next);
}

function _applyThemeIcon(theme) {
  var icon = document.getElementById('themeIcon');
  if (icon) icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
}

// Apply icon on load (theme already set by inline head script)
document.addEventListener('DOMContentLoaded', function() {
  var theme = (document.getElementById('htmlRoot') || document.documentElement)
    .getAttribute('data-theme') || 'dark';
  _applyThemeIcon(theme);
});

// ─── MODAL HELPERS ───────────────────────────
function openModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.remove('open');
    document.body.style.overflow = '';
  }
}

// Close modal on backdrop click
document.addEventListener('click', e => {
  if (e.target.classList.contains('gm-modal-backdrop')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// Close modal on Escape key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.gm-modal-backdrop.open').forEach(m => {
      m.classList.remove('open');
    });
    document.body.style.overflow = '';
  }
});

// ─── ANIMATED PROGRESS BARS ──────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Trigger animated bars
  setTimeout(() => {
    document.querySelectorAll('.animated-bar').forEach(bar => {
      const tw = getComputedStyle(bar).getPropertyValue('--tw').trim();
      if (tw) bar.style.width = tw;
    });
  }, 200);

  // Animate KPI values
  document.querySelectorAll('.kpi-value').forEach(el => {
    const target = parseInt(el.textContent.replace(/[^0-9]/g, '')) || 0;
    if (target === 0 || el.textContent.includes('%') || el.textContent.includes('$') || el.textContent.includes('/')) return;
    let current = 0;
    const step = Math.ceil(target / 30);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 30);
  });
});

// ─── CHART.JS DEFAULTS ───────────────────────
if (typeof Chart !== 'undefined') {
  var _isLight = (document.getElementById('htmlRoot') || document.documentElement)
    .getAttribute('data-theme') === 'light';
  Chart.defaults.color = _isLight ? '#4b5563' : '#8b949e';
  Chart.defaults.borderColor = _isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.07)';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = _isLight ? '#ffffff' : '#161b22';
  Chart.defaults.plugins.tooltip.borderColor = _isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.titleColor = _isLight ? '#1e2533' : '#e6edf3';
  Chart.defaults.plugins.tooltip.bodyColor = _isLight ? '#4b5563' : '#8b949e';
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
}

// ─── TOAST NOTIFICATION ──────────────────────
function showToast(msg, type = 'success') {
  const colors = {
    success: { bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.25)', color: '#6ee7b7', icon: 'bi-check-circle' },
    danger: { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.25)', color: '#fca5a5', icon: 'bi-x-circle' },
    info: { bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.25)', color: '#93c5fd', icon: 'bi-info-circle' },
  };
  const c = colors[type] || colors.success;
  const toast = document.createElement('div');
  toast.style.cssText = `
    position: fixed; top: 80px; right: 1.5rem; z-index: 9999;
    background: ${c.bg}; border: 1px solid ${c.border}; color: ${c.color};
    padding: .75rem 1.25rem; border-radius: 10px; font-size: .875rem;
    display: flex; align-items: center; gap: .6rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    animation: slideIn .2s ease;
    backdrop-filter: blur(10px);
  `;
  toast.innerHTML = `<i class="bi ${c.icon}"></i> ${msg}`;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity .3s';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ─── FETCH HELPERS ───────────────────────────
async function apiRequest(url, method = 'GET', data = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (data) opts.body = JSON.stringify(data);
  try {
    const res = await fetch(url, opts);
    return await res.json();
  } catch (err) {
    console.error('API error:', err);
    return { error: err.message };
  }
}

// ─── PROGRESS RING ANIMATION ─────────────────
document.querySelectorAll('.hero-progress-ring circle[stroke-dasharray]').forEach(el => {
  const target = parseInt(el.getAttribute('stroke-dasharray'));
  el.setAttribute('stroke-dasharray', '0 201');
  setTimeout(() => {
    el.style.transition = 'stroke-dasharray 1.5s cubic-bezier(.4,0,.2,1)';
    el.setAttribute('stroke-dasharray', `${target} 201`);
  }, 300);
});

// ─── CONFIRM DIALOG ──────────────────────────
window.gmConfirm = (msg) => confirm(msg);
