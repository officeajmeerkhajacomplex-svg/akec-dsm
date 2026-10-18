#!/usr/bin/env python3
"""Generate the small same-origin script for AKEC's collapse and dropdown navigation."""
from pathlib import Path

OUTPUT = Path("assets-optimized/akec-ui.js")
CODE = r"""(() => {
  'use strict';

  const toggleSelector = (kind) => '[data-bs-toggle="' + kind + '"]';

  function closeDropdowns(except = null) {
    document.querySelectorAll('.dropdown-menu.show').forEach((menu) => {
      const item = menu.closest('.dropdown');
      if (item === except) return;
      menu.classList.remove('show');
      item?.classList.remove('show');
      item?.querySelector(toggleSelector('dropdown'))?.setAttribute('aria-expanded', 'false');
    });
  }

  document.addEventListener('click', (event) => {
    const source = event.target instanceof Element ? event.target : event.target?.parentElement;
    if (!source) return;

    const collapseToggle = source.closest(toggleSelector('collapse'));
    if (collapseToggle) {
      const target = collapseToggle.getAttribute('data-bs-target') || collapseToggle.getAttribute('href');
      if (!target || !target.startsWith('#')) return;
      const panel = document.querySelector(target);
      if (!panel) return;
      const expanded = !panel.classList.contains('show');
      panel.classList.toggle('show', expanded);
      collapseToggle.setAttribute('aria-expanded', String(expanded));
      if (!expanded) closeDropdowns();
      return;
    }

    const dropdownToggle = source.closest(toggleSelector('dropdown'));
    if (dropdownToggle) {
      const item = dropdownToggle.closest('.dropdown');
      const menu = item?.querySelector('.dropdown-menu');
      if (!item || !menu) return;
      event.preventDefault();
      const expanded = !menu.classList.contains('show');
      closeDropdowns(item);
      item.classList.toggle('show', expanded);
      menu.classList.toggle('show', expanded);
      dropdownToggle.setAttribute('aria-expanded', String(expanded));
      return;
    }

    if (!source.closest('.dropdown')) closeDropdowns();

    const nav = source.closest('.navbar-collapse');
    if (
      nav?.classList.contains('show') &&
      source.closest('a') &&
      window.matchMedia('(max-width: 991.98px)').matches
    ) {
      nav.classList.remove('show');
      document.querySelectorAll(toggleSelector('collapse')).forEach((toggle) => {
        if (toggle.getAttribute('data-bs-target') === '#' + nav.id) {
          toggle.setAttribute('aria-expanded', 'false');
        }
      });
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const opened = document.querySelector('.dropdown-menu.show');
    if (!opened) return;
    const item = opened.closest('.dropdown');
    closeDropdowns();
    item?.querySelector(toggleSelector('dropdown'))?.focus();
  });
})();
"""

def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(CODE, encoding="utf-8")
    print(f"Generated {OUTPUT} ({OUTPUT.stat().st_size} bytes).")

if __name__ == "__main__":
    main()
