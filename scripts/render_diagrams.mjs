#!/usr/bin/env node
// Render diagrams from Mermaid sources using mermaid-cli (X-14)
// Chạy độc lập trên cả Windows, Linux và macOS qua Node.js (không phụ thuộc bash)
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");
const diagDir = path.resolve(rootDir, "docs", "diagrams");

const isWin = process.platform === "win32";
const npxCmd = isWin ? "npx.cmd" : "npx";

function render(inputFile, outputFile) {
  const inPath = path.join(diagDir, inputFile);
  const outPath = path.join(diagDir, outputFile);
  console.log(`Rendering ${inputFile} -> ${outputFile}...`);
  const res = spawnSync(
    npxCmd,
    [
      "-y",
      "@mermaid-js/mermaid-cli",
      "-i",
      inPath,
      "-o",
      outPath,
      "-b",
      "white",
    ],
    {
      stdio: "inherit",
      shell: isWin,
    }
  );

  if (res.error) {
    throw res.error;
  }
  if (res.status !== 0) {
    throw new Error(`Command failed with exit code ${res.status}`);
  }
}

try {
  render("pipeline.mmd", "pipeline.png");
  render("state_machine.mmd", "state_machine.png");
  console.log("Render diagrams completed successfully!");
} catch (err) {
  console.error("Render diagrams failed:", err.message || err);
  process.exit(1);
}

