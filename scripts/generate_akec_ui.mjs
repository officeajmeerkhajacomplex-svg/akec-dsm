import { mkdir, writeFile, unlink } from "node:fs/promises";
import path from "node:path";

const OUTPUT = path.join(process.cwd(), "assets-optimized");
const TARGET = path.join(OUTPUT, "akec-ui.js");

const code = [
  "(() => {",
  "  'use strict';",
  "  function closeDropdowns(except = null) {",
  '    document.querySelectorAll(".dropdown-menu.show").forEach((menu) => {',
  '      const item = menu.closest(".dropdown");',
  "      if (item === except) return;",
  '      menu.classList.remove("show");',
  '      item?.classList.remove("show");',
  '      item?.querySelector(\'[data-bs-toggle="dropdown"]\')?.setAttribute("aria-expanded", "false");',
  "    });",
  "  }",
  "  document.addEventListener('click', (event) => {",
  "    const source = event.target instanceof Element ? event.target : null;",
  "    if (!source) return;",
  '    const collapseToggle = source.closest(\'[data-bs-toggle="collapse"]\');',
  "    if (collapseToggle) {",
  "      const selector = collapseToggle.getAttribute('data-bs-target') || collapseToggle.getAttribute('href');",
  "      if (!selector || !selector.startsWith('#')) return;",
  "      const panel = document.querySelector(selector);",
  "      if (!panel) return;",
  '      const expanded = !panel.classList.contains("show");',
  '      panel.classList.toggle("show", expanded);',
  "      collapseToggle.setAttribute('aria-expanded', String(expanded));",
  "      if (!expanded) closeDropdowns();",
  "      return;",
  "    }",
  "    const dropdownToggle = source.closest(\'[data-bs-toggle="dropdown"]\');",
  "    if (dropdownToggle) {",
  '      const item = dropdownToggle.closest(".dropdown");',
  '      const menu = item?.querySelector(".dropdown-menu");',
  "      if (!item || !menu) return;",
  "      event.preventDefault();",
  '      const expanded = !menu.classList.contains("show");',
  "      closeDropdowns(item);",
  '      item.classList.toggle("show", expanded);',
  '      menu.classList.toggle("show", expanded);',
  "      dropdownToggle.setAttribute('aria-expanded', String(expanded));",
  "      return;",
  "    }",
  '    if (!source.closest(".dropdown")) closeDropdowns();',
  '    const nav = source.closest(".navbar-collapse");',
  '    if (nav?.classList.contains("show") && source.closest("a") &&',
  '        window.matchMedia("(max-width: 991.98px)").matches) {',
  '      nav.classList.remove("show");',
  '      const toggle = document.querySelector(\'[data-bs-toggle="collapse"][data-bs-target="#\' + nav.id + \'"]\');',
  '      toggle?.setAttribute("aria-expanded", "false");',
  "    }",
  "  });",
  "  document.addEventListener('keydown', (event) => {",
  "    if (event.key !== 'Escape') return;",
  '    const opened = document.querySelector(".dropdown-menu.show");',
  "    if (!opened) return;",
  '    const item = opened.closest(".dropdown");',
  "    closeDropdowns();",
  '    item?.querySelector(\'[data-bs-toggle="dropdown"]\')?.focus();',
  "  });",
  "})();",
].join("\\n");

async function main() {
  await mkdir(OUTPUT, { recursive: true });
  await writeFile(TARGET, code, "utf8");
  await unlink(path.join(OUTPUT, "bootstrap.bundle.min.js")).catch(() => {});
  console.log("Generated lightweight AKEC navigation script: " + Buffer.byteLength(code) + " bytes.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
