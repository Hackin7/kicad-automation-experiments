(() => {
  const bindThemeToggle = () => {
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.addEventListener('click', () => {
        const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = next;
        localStorage.setItem('theme', next);
      });
    });
  };

  const resultState = (value) => {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'success') return 'success';
    if (normalized === 'skipped') return 'skipped';
    if (normalized === 'failure' || normalized === 'failed' || normalized === 'cancelled') {
      return 'failure';
    }
    return 'neutral';
  };

  const applyPillStates = () => {
    document.querySelectorAll('[data-pill-for]').forEach((pill) => {
      const target = document.getElementById(pill.dataset.pillFor);
      if (target) pill.dataset.state = resultState(target.textContent);
    });
  };

  window.HardwareSite = { applyPillStates, resultState };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindThemeToggle);
  } else {
    bindThemeToggle();
  }
})();
