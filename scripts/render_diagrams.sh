#!/usr/bin/env bash
# Render diagrams from Mermaid sources using mermaid-cli (X-14)
# Yêu cầu: Node.js và mạng để npx tải @mermaid-js/mermaid-cli
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIAG_DIR="${ROOT_DIR}/docs/diagrams"

echo "Rendering pipeline.mmd -> pipeline.png..."
npx -y @mermaid-js/mermaid-cli -i "${DIAG_DIR}/pipeline.mmd" -o "${DIAG_DIR}/pipeline.png" -b white

echo "Rendering state_machine.mmd -> state_machine.png..."
npx -y @mermaid-js/mermaid-cli -i "${DIAG_DIR}/state_machine.mmd" -o "${DIAG_DIR}/state_machine.png" -b white

echo "Render diagrams completed successfully!"

