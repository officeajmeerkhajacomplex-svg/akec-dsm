import { readdir, mkdir, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import { PurgeCSS } from "purgecss";

const ROOT = process.cwd();
const OUTPUT = path.join(ROOT, "assets-optimized");
const CDN = "https://cdn.jsdelivr.net/npm";

async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Could not download " + url + " (HTTP " + response.status + ")");
  }
  return response.text();
}

function containsAll(css, selectors) {
  return selectors.every((selector) => css.includes(selector));
}

function restoreRemixIconFontFace(css) {
  const match = css.match(/@font-face\s*{[^}]*}/i);
  if (!match) throw new Error("Remix Icon @font-face rule was not found.");
  const family = (match[0].match(/font-family\s*:\s*([^;]+);/i) || [])[1] || "remixicon";
  const weight = (match[0].match(/font-weight\s*:\s*([^;]+);/i) || [])[1] || "normal";
  const style = (match[0].match(/font-style\s*:\s*([^;]+);/i) || [])[1] || "normal";
  const replacement =
    "@font-face{font-family:" + family.trim() +
    ";src:url('/assets-optimized/fonts/remixicon.woff2') format('woff2')" +
    ";font-weight:" + weight.trim() +
    ";font-style:" + style.trim() +
    ";font-display:swap}";
  return css.replace(match[0], replacement);
}

async function main() {
  await mkdir(OUTPUT, { recursive: true });
  const fontDir = path.join(OUTPUT, "fonts");
  await mkdir(fontDir, { recursive: true });

  const bootstrapUrl = CDN + "/bootstrap@5.3.0/dist/css/bootstrap.min.css";
  const remixUrl = CDN + "/remixicon@2.5.0/fonts/remixicon.css";
  const [bootstrapSource, remixSource] = await Promise.all([
    fetchText(bootstrapUrl),
    fetchText(remixUrl),
  ]);

  const contentFiles = (await readdir(ROOT))
    .filter((name) => name.toLowerCase().endsWith(".html"))
    .map((name) => path.join(ROOT, name));
  if (contentFiles.length < 7) {
    throw new Error("Expected the AKEC HTML pages to be present before purging vendor CSS.");
  }

  // Keep selectors that framework JavaScript adds at runtime, including collapse,
  // validation, dropdown and modal states. All eight HTML files are scanned.
  const safelist = {
    standard: [
      "show", "collapsing", "collapsed", "collapse", "active", "disabled",
      "fade", "focus", "focused", "was-validated", "is-valid", "is-invalid",
      "valid-feedback", "invalid-feedback", "visually-hidden",
      /^navbar/, /^dropdown/, /^collapse/, /^modal/, /^toast/, /^tooltip/,
      /^popover/, /^offcanvas/, /^spinner-/, /^progress-/, /^btn-close/,
      /^form-/, /^accordion/, /^carousel/, /^table-/,
    ],
  };

  const results = await new PurgeCSS().purge({
    content: contentFiles,
    css: [{ raw: bootstrapSource }, { raw: remixSource }],
    safelist,
    variables: false,
    keyframes: false,
    fontFace: false,
  });

  let bootstrapPurged = results[0]?.css || "";
  let remixPurged = results[1]?.css || "";

  // Fail safe to the original minified stylesheet if important selectors were removed.
  if (!containsAll(bootstrapPurged, [".container", ".row", ".navbar-toggler", ".collapse", ".form-control"])) {
    console.warn("A required Bootstrap selector was missing; keeping the full Bootstrap stylesheet.");
    bootstrapPurged = bootstrapSource;
  }
  if (!containsAll(remixPurged, [".ri-menu-line", ".ri-phone-fill"]) || !/@font-face/i.test(remixPurged)) {
    console.warn("A required Remix Icon selector was missing; keeping the full icon stylesheet.");
    remixPurged = remixSource;
  }

  const fontResponse = await fetch(CDN + "/remixicon@2.5.0/fonts/remixicon.woff2");
  if (!fontResponse.ok) {
    throw new Error("Could not download Remix Icon WOFF2 font (HTTP " + fontResponse.status + ").");
  }
  await writeFile(
    path.join(fontDir, "remixicon.woff2"),
    Buffer.from(await fontResponse.arrayBuffer()),
  );

  remixPurged = restoreRemixIconFontFace(remixPurged);
  const bootstrapPath = path.join(OUTPUT, "bootstrap-purged.css");
  const remixPath = path.join(OUTPUT, "remixicon-purged.css");
  await writeFile(bootstrapPath, bootstrapPurged, "utf8");
  await writeFile(remixPath, remixPurged, "utf8");

  const bootstrapBytes = (await stat(bootstrapPath)).size;
  const remixBytes = (await stat(remixPath)).size;
  const fontBytes = (await stat(path.join(fontDir, "remixicon.woff2"))).size;
  console.log("Local vendor CSS built.");
  console.log("Bootstrap: " + Buffer.byteLength(bootstrapSource) + " -> " + bootstrapBytes + " bytes");
  console.log("Remix Icon: " + Buffer.byteLength(remixSource) + " -> " + remixBytes + " bytes");
  console.log("Remix Icon WOFF2: " + fontBytes + " bytes");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
