#!/usr/bin/env bash
# Generate pinned requirements using pip-compile (pip-tools)
# Usage: ./scripts/generate_requirements.sh

set -e
pip install pip-tools
pip-compile src/llm_chat_node/requirements.in --output-file src/llm_chat_node/requirements.txt

echo "Generated pinned requirements in src/llm_chat_node/requirements.txt"
