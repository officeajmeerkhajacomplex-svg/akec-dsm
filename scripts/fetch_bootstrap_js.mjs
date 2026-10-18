import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const OUT = path.join(process.cwd(), "assets-optimized");
const URL = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js";

async function main() {
  await mkdir(OUT, { recursive: true });
  const response = await fetch(URL);
  if (!response.ok) {
    throw new Error("Could not download Bootstrap bundle (HTTP " + response.status + ").");
  }
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.byteLength < 10000 || !bytes.toString("utf8", 0, 500).includes("Bootstrap")) {
    throw new Error("Downloaded Bootstrap file failed basic integrity checks.");
  }
  const file = path.join(OUT, "bootstrap.bundle.min.js");
  await writeFile(file, bytes);
  console.log("Self-hosted Bootstrap bundle: " + bytes.byteLength + " bytes.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
