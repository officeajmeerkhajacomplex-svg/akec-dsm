import { readdir, mkdir, readFile, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import { PurgeCSS } from "purgecss";

const ROOT = process.cwd();
const OUTPUT = path.join(ROOT, "assets-optimized");
const CDN = "https://cdn.jsdelivr.net/npm";
const PAGE_NAMES = [
  "index.html", "about.html", "admission.html", "contact.html",
  "dawa.html", "garden.html", "hifz.html", "madrassa.html",
];

const safelist = {
  standard: [
    "show", "collapsing", "collapsed", "collapse", "active", "disabled",
    "fade", "focus", "focused", "was-validated", "is-valid", "is-invalid",
    "valid-feedback", "invalid-feedback", "visually-hidden",
    "modal-open", "modal-backdrop", "modal-static", "offcanvas-backdrop",
    "showing", "hiding", "tooltip", "popover",
  ],
};

async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Could not download " + url + " (HTTP " + response.status + ")");
  return response.text();
}

function hasSelectors(css, selectors) {
  return selectors.every((selector) => css.includes(selector));
}

async function main() {
  await mkdir(OUTPUT, { recursive: true });
  const bootstrap = await fetchText(
    CDN + "/bootstrap@5.3.0/dist/css/bootstrap.min.css",
  );
  const globalPath = path.join(OUTPUT, "bootstrap-purged.css");
  const globalFallback = (await readFile(globalPath, "utf8").catch(() => bootstrap));

  const available = new Set(await readdir(ROOT));
  for (const page of PAGE_NAMES) {
    if (!available.has(page)) throw new Error("Expected page missing: " + page);
    const html = await readFile(path.join(ROOT, page), "utf8");
    const result = await new PurgeCSS().purge({
      content: [{ raw: html, extension: "html" }],
      css: [{ raw: bootstrap }],
      safelist,
      variables: false,
      keyframes: false,
      fontFace: false,
    });

    let output = result[0]?.css || "";
    const required = [".container", ".row", ".navbar-toggler", ".navbar-collapse", ".collapse"];
    if (page === "admission.html") required.push(".form-control", ".form-select", ".form-label");

    if (!hasSelectors(output, required)) {
      console.warn(page + ": missing essential selector; using the global purged stylesheet.");
      output = globalFallback;
    }
    const file = "bootstrap-purged-" + path.basename(page, ".html") + ".css";
    await writeFile(path.join(OUTPUT, file), output, "utf8");
    console.log(
      file + ": " + (await stat(path.join(OUTPUT, file))).size +
      " bytes (global: " + (await stat(globalPath).catch(() => ({ size: Buffer.byteLength(bootstrap) }))).size + ")",
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
